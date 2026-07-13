"""stores/vectordb/providers/pgvector/search.py — retrieval queries.

Split out of `PGVectorProvider.py` (003 refactor Phase 4b). The four retrieval
methods: dense vector search, dense vector search with JSONB pre-filter,
sparse full-text (BM25) search, and sparse full-text search with JSONB
pre-filter.

All functions take db client + logger explicitly. The repeated
row → RetrievedDocument mapping is factored into one helper (no behavior
change — identical parsing logic).
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata

from sqlalchemy.sql import text as sql_text

from models.db_schemes import RetrievedDocument
from ...VectorDBEnums import PgVectorTableSchemeEnums
from .schema import _validate_identifier, is_collection_existed


def _to_retrieved_document(record) -> RetrievedDocument:
    """Map one SQL row to a RetrievedDocument, parsing metadata lazily."""
    return RetrievedDocument(
        text=record.text,
        score=record.score if isinstance(record.score, float) else float(record.score),
        metadata=(
            record.metadata
            if isinstance(record.metadata, dict)
            else json.loads(record.metadata or "{}")
        ),
    )


_ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F]")
_AR_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u0640]"
)


def _normalize_query_for_bm25(text: str) -> str:
    """Lightweight Arabic normalisation for BM25 tsquery."""
    if not text:
        return ""
    if not _ARABIC_CHAR_RE.search(text):
        return text

    normalized = unicodedata.normalize("NFKC", text)
    normalized = _AR_DIACRITICS_RE.sub("", normalized)
    normalized = re.sub(r"[أإآٱ]", "ا", normalized)
    normalized = re.sub(r"[ىي]", "ي", normalized)
    normalized = re.sub(r"ة", "ه", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _build_tsquery(query: str) -> str:
    """tsquery string: whitespace tokens, prefix-matched (token:*), joined with AND (&)."""
    query = _normalize_query_for_bm25(query)
    raw_terms = [t.strip() for t in (query or "").split() if len(t.strip()) >= 2]
    if not raw_terms:
        return ""
    return " & ".join(f"{t}:*" for t in raw_terms)


async def search_by_vector(db_client, logger: logging.Logger, collection_name: str, vector: list, limit: int):
    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(f"Can not search for records in a non-existed collection: {collection_name}")
        return False

    vector = "[" + ",".join([str(v) for v in vector]) + "]"
    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(f'SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, '
                                  f'{PgVectorTableSchemeEnums.METADATA.value} as metadata, '
                                  f'1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) as score'
                                  f' FROM "{collection_name}"'
                                  ' ORDER BY score DESC '
                                  'LIMIT :limit'
                                  )

            result = await session.execute(search_sql, {"vector": vector, "limit": safe_limit})

            records = result.fetchall()

            return [_to_retrieved_document(record) for record in records]


async def search_by_vector_filtered(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    vector: list,
    limit: int,
    metadata_filter: dict | None = None,
):
    """Dense vector search with an optional JSONB containment pre-filter."""
    if not metadata_filter:
        return await search_by_vector(db_client, logger, collection_name, vector, limit)

    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(
            f"Can not search (filtered) in non-existed collection: {collection_name}"
        )
        return False

    vec_str = "[" + ",".join(str(v) for v in vector) + "]"
    filter_json = json.dumps(metadata_filter, ensure_ascii=False)

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) AS score '
                f'FROM "{collection_name}" '
                f'WHERE {PgVectorTableSchemeEnums.METADATA.value} @> :filter::jsonb '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            result = await session.execute(
                search_sql,
                {"vector": vec_str, "filter": filter_json, "limit": safe_limit},
            )
            records = result.fetchall()

    return [_to_retrieved_document(record) for record in records]


async def search_by_text(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    query: str,
    limit: int,
    language: str = "simple",
):
    """Full-text (sparse) search using PostgreSQL tsvector."""
    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(
            f"Can not run text search in non-existed collection: {collection_name}"
        )
        return []

    tsquery_str = _build_tsquery(query)
    if not tsquery_str:
        return []

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'ts_rank_cd(to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}), '
                f'           to_tsquery(:lang, :tsquery)) AS score '
                f'FROM "{collection_name}" '
                f'WHERE to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}) '
                f'      @@ to_tsquery(:lang, :tsquery) '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            try:
                result = await session.execute(
                    search_sql,
                    {"lang": language, "tsquery": tsquery_str, "limit": safe_limit},
                )
                records = result.fetchall()
            except Exception as exc:
                logger.warning(f"BM25 search failed (tsquery={tsquery_str!r}): {exc}")
                return []

    return [_to_retrieved_document(record) for record in records]


async def search_by_text_filtered(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    query: str,
    limit: int,
    metadata_filter: dict | None = None,
    language: str = "simple",
):
    """Full-text (sparse) search with an optional JSONB metadata pre-filter."""
    if not metadata_filter:
        return await search_by_text(
            db_client, logger,
            collection_name=collection_name,
            query=query,
            limit=limit,
            language=language,
        )

    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(
            f"Can not run filtered text search in non-existed collection: {collection_name}"
        )
        return []

    tsquery_str = _build_tsquery(query)
    if not tsquery_str:
        return []

    filter_json = json.dumps(metadata_filter, ensure_ascii=False)

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'ts_rank_cd(to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}), '
                f'           to_tsquery(:lang, :tsquery)) AS score '
                f'FROM "{collection_name}" '
                f'WHERE {PgVectorTableSchemeEnums.METADATA.value} @> :filter::jsonb '
                f'  AND to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}) '
                f'      @@ to_tsquery(:lang, :tsquery) '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            try:
                result = await session.execute(
                    search_sql,
                    {
                        "lang": language,
                        "tsquery": tsquery_str,
                        "filter": filter_json,
                        "limit": safe_limit,
                    },
                )
                records = result.fetchall()
            except Exception as exc:
                logger.warning(
                    f"Filtered BM25 search failed (tsquery={tsquery_str!r}): {exc}"
                )
                return []

    return [_to_retrieved_document(record) for record in records]


def _validate_field_key(field_key: str) -> str:
    """JSONB keys allow letters, digits, underscore, space."""
    if not field_key or not all(ch.isalnum() or ch in "_ " for ch in field_key):
        raise ValueError(f"Unsafe field key: {field_key!r}")
    return field_key


def _build_scope_where(
    *,
    entity_key: str | None = None,
    entity_prefix: str | None = None,
    field_key: str | None = None,
    metadata_filter: dict | None = None,
) -> tuple[str, dict]:
    """Build parameterized WHERE fragments for entity/field scoped retrieval."""
    clauses: list[str] = []
    params: dict = {}

    if entity_key and entity_prefix:
        entity_key = _validate_field_key(entity_key)
        prefix = (entity_prefix or "").strip().upper()
        if prefix:
            clauses.append(
                f"UPPER({PgVectorTableSchemeEnums.METADATA.value} ->> :entity_key) LIKE :entity_prefix"
            )
            params["entity_key"] = entity_key
            params["entity_prefix"] = f"{prefix}%"

    if field_key:
        field_key = _validate_field_key(field_key)
        clauses.append(
            f"COALESCE({PgVectorTableSchemeEnums.METADATA.value} ->> :field_key, '') <> ''"
        )
        params["field_key"] = field_key

    if metadata_filter:
        clauses.append(f"{PgVectorTableSchemeEnums.METADATA.value} @> :filter::jsonb")
        params["filter"] = json.dumps(metadata_filter, ensure_ascii=False)

    if not clauses:
        return "", params

    return " WHERE " + " AND ".join(clauses), params


async def search_by_vector_field(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    vector: list,
    limit: int,
    field_key: str,
    field_value: str | None = None,
):
    """Dense vector search restricted to rows where ``field_key`` is present."""
    collection_name = _validate_identifier(collection_name)
    field_key = _validate_field_key(field_key)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(f"Cannot field-search non-existent collection: {collection_name}")
        return False

    vec_str = "[" + ",".join(str(v) for v in vector) + "]"

    if field_value is not None:
        where_clause = (
            f"WHERE {PgVectorTableSchemeEnums.METADATA.value} ->> :fkey = :fval "
        )
        params = {"vector": vec_str, "fkey": field_key, "fval": field_value, "limit": safe_limit}
    else:
        where_clause = (
            f"WHERE COALESCE({PgVectorTableSchemeEnums.METADATA.value} ->> :fkey, '') <> '' "
        )
        params = {"vector": vec_str, "fkey": field_key, "limit": safe_limit}

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) AS score '
                f'FROM "{collection_name}" '
                f'{where_clause}'
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            result = await session.execute(search_sql, params)
            records = result.fetchall()

    return [_to_retrieved_document(record) for record in records]


async def search_by_text_field(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    query: str,
    limit: int,
    field_key: str,
    field_value: str | None = None,
    language: str = "simple",
):
    """Full-text (sparse) search restricted to rows where ``field_key`` is present."""
    collection_name = _validate_identifier(collection_name)
    field_key = _validate_field_key(field_key)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(f"Cannot field-text-search non-existent collection: {collection_name}")
        return []

    tsquery_str = _build_tsquery(query)
    if not tsquery_str:
        return []

    if field_value is not None:
        field_clause = f"{PgVectorTableSchemeEnums.METADATA.value} ->> :fkey = :fval"
        params = {
            "lang": language, "tsquery": tsquery_str, "fkey": field_key,
            "fval": field_value, "limit": safe_limit,
        }
    else:
        field_clause = (
            f"COALESCE({PgVectorTableSchemeEnums.METADATA.value} ->> :fkey, '') <> ''"
        )
        params = {
            "lang": language, "tsquery": tsquery_str, "fkey": field_key,
            "limit": safe_limit,
        }

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'ts_rank_cd(to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}), '
                f'           to_tsquery(:lang, :tsquery)) AS score '
                f'FROM "{collection_name}" '
                f'WHERE {field_clause} '
                f'  AND to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}) '
                f'      @@ to_tsquery(:lang, :tsquery) '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            try:
                result = await session.execute(search_sql, params)
                records = result.fetchall()
            except Exception as exc:
                logger.warning(
                    f"Field BM25 search failed (tsquery={tsquery_str!r}): {exc}"
                )
                return []

    return [_to_retrieved_document(record) for record in records]


async def search_by_vector_scoped(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    vector: list,
    limit: int,
    *,
    entity_key: str | None = None,
    entity_prefix: str | None = None,
    field_key: str | None = None,
    metadata_filter: dict | None = None,
):
    """Dense vector search with entity-prefix and/or field-presence pre-filters."""
    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(f"Cannot scoped-search non-existent collection: {collection_name}")
        return False

    where_sql, scope_params = _build_scope_where(
        entity_key=entity_key,
        entity_prefix=entity_prefix,
        field_key=field_key,
        metadata_filter=metadata_filter,
    )
    if not where_sql:
        return await search_by_vector(db_client, logger, collection_name, vector, limit)

    vec_str = "[" + ",".join(str(v) for v in vector) + "]"
    params = {"vector": vec_str, "limit": safe_limit, **scope_params}

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'1 - ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) AS score '
                f'FROM "{collection_name}"'
                f'{where_sql} '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            result = await session.execute(search_sql, params)
            records = result.fetchall()

    return [_to_retrieved_document(record) for record in records]


async def search_by_text_scoped(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    query: str,
    limit: int,
    *,
    entity_key: str | None = None,
    entity_prefix: str | None = None,
    field_key: str | None = None,
    metadata_filter: dict | None = None,
    language: str = "simple",
):
    """BM25 search with entity-prefix and/or field-presence pre-filters."""
    collection_name = _validate_identifier(collection_name)
    safe_limit = max(1, min(int(limit), 200))

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.error(f"Cannot scoped text-search non-existent collection: {collection_name}")
        return []

    tsquery_str = _build_tsquery(query)
    if not tsquery_str:
        return []

    where_sql, scope_params = _build_scope_where(
        entity_key=entity_key,
        entity_prefix=entity_prefix,
        field_key=field_key,
        metadata_filter=metadata_filter,
    )
    if not where_sql:
        return await search_by_text(
            db_client, logger, collection_name, query, limit, language=language
        )

    params = {
        "lang": language,
        "tsquery": tsquery_str,
        "limit": safe_limit,
        **scope_params,
    }

    async with db_client() as session:
        async with session.begin():
            search_sql = sql_text(
                f'SELECT {PgVectorTableSchemeEnums.TEXT.value} AS text, '
                f'{PgVectorTableSchemeEnums.METADATA.value} AS metadata, '
                f'ts_rank_cd(to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}), '
                f'           to_tsquery(:lang, :tsquery)) AS score '
                f'FROM "{collection_name}"'
                f'{where_sql} '
                f'  AND to_tsvector(:lang, {PgVectorTableSchemeEnums.TEXT.value}) '
                f'      @@ to_tsquery(:lang, :tsquery) '
                'ORDER BY score DESC '
                'LIMIT :limit'
            )
            try:
                result = await session.execute(search_sql, params)
                records = result.fetchall()
            except Exception as exc:
                logger.warning(f"Scoped BM25 search failed (tsquery={tsquery_str!r}): {exc}")
                return []

    return [_to_retrieved_document(record) for record in records]

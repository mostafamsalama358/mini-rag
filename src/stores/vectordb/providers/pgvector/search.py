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
_TSQUERY_TOKEN_RE = re.compile(r"[A-Za-z0-9\u0600-\u06FF]{2,}")
# Drop high-frequency fillers so the 12-token budget keeps content terms.
_BM25_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "was",
        "what",
        "when",
        "which",
        "who",
        "why",
        "with",
    }
)


def _normalize_query_for_bm25(text: str) -> str:
    """Normalise query text before BM25 tokenisation.

    Always strips punctuation that breaks ``to_tsquery`` (``.``, ``,``, ``%``,
    ``?``, ``:``, …). Applies extra Arabic letter folding when Arabic is present.
    """
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    if _ARABIC_CHAR_RE.search(normalized):
        normalized = _AR_DIACRITICS_RE.sub("", normalized)
        normalized = re.sub(r"[أإآٱ]", "ا", normalized)
        normalized = re.sub(r"[ىي]", "ي", normalized)
        normalized = re.sub(r"ة", "ه", normalized)

    # Strip punctuation/symbols; keep letters, digits, underscore, whitespace.
    # Hyphen is removed so ``flurest-n`` → tokens ``flurest`` / ``n`` (``-`` is
    # the NOT operator in ``to_tsquery``).
    normalized = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _build_tsquery(query: str) -> str:
    """Safe ``to_tsquery`` string: alnum tokens, prefix-matched, AND-joined.

    User questions often contain ``0.1%``, ``nose.``, ``why?``, ``brufen,`` —
    those must never become ``0.1%,:*`` / ``nose.:*`` / ``why?:*``.
    """
    query = _normalize_query_for_bm25(query)
    raw_terms: list[str] = []
    seen: set[str] = set()
    for match in _TSQUERY_TOKEN_RE.finditer(query or ""):
        term = match.group(0)
        if term.isdigit():
            continue
        key = term.casefold()
        if key in seen or key in _BM25_STOPWORDS:
            continue
        seen.add(key)
        raw_terms.append(term)
        if len(raw_terms) >= 6:
            break
    if not raw_terms:
        return ""
    return " & ".join(f"{t}:*" for t in raw_terms)


def _build_scoped_bm25_query(
    query: str,
    *,
    entity_prefix: str | None = None,
    field_key: str | None = None,
) -> str:
    """Focused BM25 text for entity/field scopes (avoids over-AND of full questions).

    When ``field_key`` is set, include field + entity + a few content words.
    When soft-retrying without field (metadata incomplete), use **entity tokens
    only** so product-header chunks still match even if they lack pregnancy text.
    """
    parts: list[str] = []
    if field_key:
        fk = str(field_key).replace("_", " ").strip()
        if fk and fk.lower() not in {"unknown", "product name"}:
            parts.append(fk)
    if entity_prefix:
        parts.extend(_entity_scope_tokens(entity_prefix)[:2])
    if field_key:
        skip = {p.casefold() for p in parts}
        for match in _TSQUERY_TOKEN_RE.finditer(_normalize_query_for_bm25(query)):
            term = match.group(0)
            key = term.casefold()
            if term.isdigit() or key in _BM25_STOPWORDS or key in skip:
                continue
            parts.append(term)
            skip.add(key)
            if len(parts) >= 5:
                break
    if parts:
        return " ".join(parts)
    return query



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
                f'WHERE {PgVectorTableSchemeEnums.METADATA.value} @> CAST(:filter AS jsonb) '
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
                f'WHERE {PgVectorTableSchemeEnums.METADATA.value} @> CAST(:filter AS jsonb) '
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


_ENTITY_SCOPE_STOPWORDS = frozenset(
    {
        "MG",
        "ML",
        "G",
        "MCG",
        "IU",
        "TABLET",
        "TABLETS",
        "CAPSULE",
        "CAPSULES",
        "FILM",
        "COATED",
        "YEAR",
        "YEARS",
        "UNDER",
        "OVER",
        "ADULT",
        "ADULTS",
        "ADOLESCENT",
        "ADOLESCENTS",
        "CHILD",
        "CHILDREN",
        "PATIENT",
        "PATIENTS",
        "THE",
        "AND",
        "FOR",
        "WITH",
        "FROM",
        "EACH",
        "CONTAINS",
        "INCLUDING",
        "USED",
        "TAKE",
        "TAKING",
        # Pack/form noise only — keep product-line tokens (ADVANCE/EXTRA/JOINT…)
        "EVOHALER",
        "INHALER",
        "SUSPENSION",
        "SYRUP",
        "DROPS",
        "CREAM",
        "GEL",
        "LOZENGE",
        "LOZENGES",
        "CAPLET",
        "CAPLETS",
        "SACHET",
        "SACHETS",
        "ER",
        "FC",
        "FCT",
    }
)


def _entity_scope_tokens(entity_prefix: str) -> list[str]:
    """Significant tokens for scoped entity match (order preserved, max 4).

    Dose/form noise is dropped, but product-line tokens such as ADVANCE / EXTRA /
    JOINT / COLD / FLU are kept so ``Panadol Extra`` does not match
    ``Panadol Advance``.
    """
    import re

    parts = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", entity_prefix or "")
    tokens: list[str] = []
    for part in parts:
        upper = part.upper()
        if upper in _ENTITY_SCOPE_STOPWORDS:
            continue
        if upper not in tokens:
            tokens.append(upper)
        if len(tokens) >= 4:
            break
    return tokens


def brand_head_fallback_prefix(entity_prefix: str) -> str | None:
    """If prefix is a multi-token product line, return brand-head-only fallback.

    Used only when the precise product-line scope returns zero rows (legacy
    rows indexed as bare brand). Does not run inside the primary SQL predicate,
    so Extra/Advance stay distinct when both are indexed.
    """
    tokens = _entity_scope_tokens(entity_prefix)
    if len(tokens) < 2:
        return None
    return tokens[0]


def _build_scope_where(
    *,
    entity_key: str | None = None,
    entity_prefix: str | None = None,
    entity_prefixes: list[str] | None = None,
    field_key: str | None = None,
    metadata_filter: dict | None = None,
) -> tuple[str, dict]:
    """Build parameterized WHERE fragments for entity/field scoped retrieval.

    ``entity_prefixes`` matches ANY listed brand (OR). Each brand still uses
    AND across its significant tokens so ``Panadol Extra`` ≠ ``Panadol Advance``.

    ``field_key`` is treated as a logical field name when matching
    ``metadata.field_name`` / ``metadata.field_names``, while still supporting
    the legacy "JSON key is present" check used by tabular column scopes.
    """
    clauses: list[str] = []
    params: dict = {}
    meta_col = PgVectorTableSchemeEnums.METADATA.value

    prefixes: list[str] = []
    for raw in list(entity_prefixes or []) + ([entity_prefix] if entity_prefix else []):
        text = (raw or "").strip()
        if text and text not in prefixes:
            prefixes.append(text)
        if len(prefixes) >= 8:
            break

    resolved_entity_key = entity_key or ("entity" if prefixes else None)
    if resolved_entity_key and prefixes:
        resolved_entity_key = _validate_field_key(resolved_entity_key)
        params["entity_key"] = resolved_entity_key
        entity_expr = f"UPPER({meta_col} ->> :entity_key)"
        aliases_expr = (
            f"UPPER(COALESCE({meta_col} ->> 'entity_aliases', ''))"
        )
        haystack = f"({entity_expr} || ' ' || {aliases_expr})"

        entity_groups: list[str] = []
        tok_i = 0
        for prefix in prefixes:
            tokens = _entity_scope_tokens(prefix)
            if not tokens:
                token = prefix.strip().upper()
                if not token:
                    continue
                key = f"entity_tok_{tok_i}"
                tok_i += 1
                entity_groups.append(f"{haystack} LIKE :{key}")
                params[key] = f"%{token}%"
                continue
            token_clauses: list[str] = []
            for tok in tokens:
                key = f"entity_tok_{tok_i}"
                tok_i += 1
                token_clauses.append(f"{haystack} LIKE :{key}")
                params[key] = f"%{tok}%"
            entity_groups.append("(" + " AND ".join(token_clauses) + ")")
        if entity_groups:
            if len(entity_groups) == 1:
                clauses.append(entity_groups[0])
            else:
                clauses.append("(" + " OR ".join(entity_groups) + ")")

    if field_key:
        field_key = _validate_field_key(field_key)
        # Prefer exact field_name. field_names is only a fallback when the
        # primary field_name is empty — otherwise interaction splits that list
        # dosage/warnings as secondary tags pollute dosage/indications searches.
        clauses.append(
            "("
            f"{meta_col} ->> 'field_name' = :logical_field "
            f"OR ("
            f"COALESCE({meta_col} ->> 'field_name', '') = '' "
            f"AND COALESCE({meta_col} -> 'field_names', '[]'::jsonb) ? :logical_field"
            f") "
            f"OR COALESCE({meta_col} ->> :field_key, '') <> ''"
            ")"
        )
        params["logical_field"] = field_key
        params["field_key"] = field_key

    if metadata_filter:
        clauses.append(f"{meta_col} @> CAST(:filter AS jsonb)")
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

    meta = PgVectorTableSchemeEnums.METADATA.value
    if field_value is not None:
        where_clause = f"WHERE {meta} ->> :fkey = :fval "
        params = {"vector": vec_str, "fkey": field_key, "fval": field_value, "limit": safe_limit}
    else:
        # Exact field_name, or field_names only when field_name is unset.
        where_clause = (
            "WHERE ("
            f"{meta} ->> 'field_name' = :logical_field "
            f"OR ("
            f"COALESCE({meta} ->> 'field_name', '') = '' "
            f"AND COALESCE({meta} -> 'field_names', '[]'::jsonb) ? :logical_field"
            f") "
            f"OR COALESCE({meta} ->> :fkey, '') <> ''"
            ") "
        )
        params = {
            "vector": vec_str,
            "fkey": field_key,
            "logical_field": field_key,
            "limit": safe_limit,
        }

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
        meta = PgVectorTableSchemeEnums.METADATA.value
        field_clause = (
            f"("
            f"{meta} ->> 'field_name' = :logical_field "
            f"OR ("
            f"COALESCE({meta} ->> 'field_name', '') = '' "
            f"AND COALESCE({meta} -> 'field_names', '[]'::jsonb) ? :logical_field"
            f") "
            f"OR COALESCE({meta} ->> :fkey, '') <> ''"
            f")"
        )
        params = {
            "lang": language, "tsquery": tsquery_str, "fkey": field_key,
            "logical_field": field_key, "limit": safe_limit,
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
    entity_prefixes: list[str] | None = None,
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
        entity_prefixes=entity_prefixes,
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
    entity_prefixes: list[str] | None = None,
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

    focus_prefix = entity_prefix
    if not focus_prefix and entity_prefixes:
        focus_prefix = entity_prefixes[0]
    bm25_text = (
        _build_scoped_bm25_query(
            query,
            entity_prefix=focus_prefix,
            field_key=field_key,
        )
        if (entity_prefix or entity_prefixes or field_key)
        else query
    )
    tsquery_str = _build_tsquery(bm25_text)
    if not tsquery_str:
        return []

    where_sql, scope_params = _build_scope_where(
        entity_key=entity_key,
        entity_prefix=entity_prefix,
        entity_prefixes=entity_prefixes,
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

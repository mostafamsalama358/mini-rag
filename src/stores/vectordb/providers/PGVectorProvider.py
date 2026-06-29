from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import (DistanceMethodEnums, PgVectorTableSchemeEnums, 
                             PgVectorDistanceMethodEnums, PgVectorIndexTypeEnums)
import logging
import re
from typing import List
from models.db_schemes import RetrievedDocument
from sqlalchemy.sql import text as sql_text
import json

# Identifiers (table/index names) cannot be bound as parameters in pgvector
# SQL, so they are interpolated via f-strings. Validate them against a strict
# allow-list so project-derived names can never become an injection vector.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, field: str = "collection_name") -> str:
    """Allow-list a SQL identifier (table/index name) before interpolation."""
    if not value or not _IDENTIFIER_RE.match(str(value)):
        raise ValueError(f"Invalid {field}: {value!r}")
    return str(value)

class PGVectorProvider(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int = 786,
                       distance_method: str = None, index_threshold: int=100):
        
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        
        self.index_threshold = index_threshold

        if distance_method == DistanceMethodEnums.COSINE.value:
            distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            distance_method = PgVectorDistanceMethodEnums.DOT.value

        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value
        self.distance_method = distance_method

        self.logger = logging.getLogger("uvicorn")
        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"


    async def connect(self):
        async with self.db_client() as session:
            try:
                # Check if vector extension already exists
                result = await session.execute(sql_text(
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                ))
                extension_exists = result.scalar_one_or_none()
                
                if not extension_exists:
                    # Only create if it doesn't exist
                    await session.execute(sql_text("CREATE EXTENSION vector"))
                    await session.commit()
            except Exception as e:
                # If extension already exists or any other error, just log and continue
                self.logger.warning(f"Vector extension setup: {str(e)}")
                await session.rollback()

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:

        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(f'SELECT * FROM pg_tables WHERE tablename = :collection_name')
                results = await session.execute(list_tbl, {"collection_name": collection_name})
                record = results.scalar_one_or_none()

        return record
    
    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix')
                results = await session.execute(list_tbl, {"prefix": self.pgvector_table_prefix})
                records = results.scalars().all()
        
        return records
    
    async def get_collection_info(self, collection_name: str) -> dict:
        collection_name = _validate_identifier(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text('''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes 
                    FROM pg_tables 
                    WHERE tablename = :collection_name
                ''')

                table_info = await session.execute(
                    table_info_sql, {"collection_name": collection_name}
                )
                table_data = table_info.fetchone()
                if not table_data:
                    return None

                count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
                record_count = await session.execute(count_sql)

                return {
                    "table_info": {
                        "schemaname": table_data[0],
                        "tablename": table_data[1],
                        "tableowner": table_data[2],
                        "tablespace": table_data[3],
                        "hasindexes": table_data[4],
                    },
                    "record_count": record_count.scalar_one(),
                }
            
    async def delete_collection(self, collection_name: str):
        collection_name = _validate_identifier(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection: {collection_name}")

                delete_sql = sql_text(f'DROP TABLE IF EXISTS "{collection_name}"')
                await session.execute(delete_sql)
                await session.commit()
        
        return True

    async def create_collection(self, collection_name: str,
                                      embedding_size: int,
                                      do_reset: bool = False):
        
        collection_name = _validate_identifier(collection_name)

        if do_reset:
            _ = await self.delete_collection(collection_name=collection_name)

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.info(f"Creating collection: {collection_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_sql = sql_text(
                        f'CREATE TABLE "{collection_name}" ('
                            f'{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY,'
                            f'{PgVectorTableSchemeEnums.TEXT.value} text, '
                            f'{PgVectorTableSchemeEnums.VECTOR.value} vector({int(embedding_size)}), '
                            f'{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT \'{{}}\', '
                            f'{PgVectorTableSchemeEnums.CHUNK_ID.value} integer, '
                            f'FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks(chunk_id)'
                        ')'
                    )
                    await session.execute(create_sql)
                    
                    # Create GIN index for full-text search (BM25)
                    text_idx_sql = sql_text(
                        f'CREATE INDEX IF NOT EXISTS "{collection_name}_tsvector_idx" '
                        f'ON "{collection_name}" USING GIN (to_tsvector(\'simple\', {PgVectorTableSchemeEnums.TEXT.value}))'
                    )
                    await session.execute(text_idx_sql)
                    
                    # Create GIN index for metadata containment filtering
                    metadata_idx_sql = sql_text(
                        f'CREATE INDEX IF NOT EXISTS "{collection_name}_metadata_gin_idx" '
                        f'ON "{collection_name}" USING GIN ({PgVectorTableSchemeEnums.METADATA.value}) '
                        f'WHERE {PgVectorTableSchemeEnums.METADATA.value} IS NOT NULL'
                    )
                    await session.execute(metadata_idx_sql)

                    await session.commit()
            
            return True

        return False
    
    async def is_index_existed(self, collection_name: str) -> bool:
        collection_name = _validate_identifier(collection_name)
        index_name = self.default_index_name(collection_name)
        _validate_identifier(index_name, field="index_name")
        async with self.db_client() as session:
            async with session.begin():
                check_sql = sql_text(f""" 
                                    SELECT 1 
                                    FROM pg_indexes 
                                    WHERE tablename = :collection_name
                                    AND indexname = :index_name
                                    """)
                results = await session.execute(check_sql, {"index_name": index_name, "collection_name": collection_name})
                
                return bool(results.scalar_one_or_none())
            
    async def create_vector_index(self, collection_name: str,
                                        index_type: str = PgVectorIndexTypeEnums.HNSW.value):
        collection_name = _validate_identifier(collection_name)
        is_index_existed = await self.is_index_existed(collection_name=collection_name)
        if is_index_existed:
            return False
        
        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
                result = await session.execute(count_sql)
                records_count = result.scalar_one()

                if records_count < self.index_threshold:
                    return False
                
                self.logger.info(f"START: Creating vector index for collection: {collection_name}")
                
                index_name = self.default_index_name(collection_name)
                _validate_identifier(index_name, field="index_name")
                create_idx_sql = sql_text(
                                            f'CREATE INDEX "{index_name}" ON "{collection_name}" '
                                            f'USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method})'
                                          )

                await session.execute(create_idx_sql)

                self.logger.info(f"END: Created vector index for collection: {collection_name}")

    async def reset_vector_index(self, collection_name: str, 
                                       index_type: str = PgVectorIndexTypeEnums.HNSW.value) -> bool:
        
        collection_name = _validate_identifier(collection_name)
        index_name = self.default_index_name(collection_name)
        _validate_identifier(index_name, field="index_name")
        async with self.db_client() as session:
            async with session.begin():
                drop_sql = sql_text(f'DROP INDEX IF EXISTS "{index_name}"')
                await session.execute(drop_sql)
        
        return await self.create_vector_index(collection_name=collection_name, index_type=index_type)

    
    async def insert_one(self, collection_name: str, text: str, vector: list,
                            metadata: dict = None,
                            record_id: str = None):
        
        collection_name = _validate_identifier(collection_name)
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not insert new record to non-existed collection: {collection_name}")
            return False
        
        if not record_id:
            self.logger.error(f"Can not insert new record without chunk_id: {collection_name}")
            return False
        
        async with self.db_client() as session:
            async with session.begin():
                insert_sql = sql_text(f'INSERT INTO "{collection_name}" '
                                      f'({PgVectorTableSchemeEnums.TEXT.value}, {PgVectorTableSchemeEnums.VECTOR.value}, {PgVectorTableSchemeEnums.METADATA.value}, {PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                      'VALUES (:text, :vector, :metadata, :chunk_id)'
                                      )
                
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_sql, {
                    'text': text,
                    'vector': "[" + ",".join([ str(v) for v in vector ]) + "]",
                    'metadata': metadata_json,
                    'chunk_id': record_id
                })
                await session.commit()

                await self.create_vector_index(collection_name=collection_name)
        
        return True
    

    async def get_indexed_chunk_ids(self, collection_name: str) -> set[int]:
        collection_name = _validate_identifier(collection_name)
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            return set()

        async with self.db_client() as session:
            async with session.begin():
                list_sql = sql_text(
                    f'SELECT {PgVectorTableSchemeEnums.CHUNK_ID.value} '
                    f'FROM "{collection_name}" '
                    f'WHERE {PgVectorTableSchemeEnums.CHUNK_ID.value} IS NOT NULL'
                )
                result = await session.execute(list_sql)
                return {row[0] for row in result.all() if row[0] is not None}

    async def insert_many(self, collection_name: str, texts: list,
                         vectors: list, metadata: list = None,
                         record_ids: list = None, batch_size: int = 50,
                         create_index: bool = True):
        
        collection_name = _validate_identifier(collection_name)
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not insert new records to non-existed collection: {collection_name}")
            return False
        
        if len(vectors) != len(record_ids):
            self.logger.error(f"Invalid data items for collection: {collection_name}")
            return False
        
        if not metadata or len(metadata) == 0:
            metadata = [None] * len(texts)
        
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i + batch_size]
                    batch_metadata = metadata[i:i + batch_size]
                    batch_record_ids = record_ids[i:i + batch_size]

                    values = []

                    for _text, _vector, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadata, batch_record_ids):
                        
                        metadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"
                        values.append({
                            'text': _text,
                            'vector': "[" + ",".join([ str(v) for v in _vector ]) + "]",
                            'metadata': metadata_json,
                            'chunk_id': _record_id
                        })
                    
                    batch_insert_sql = sql_text(f'INSERT INTO "{collection_name}" '
                                    f'({PgVectorTableSchemeEnums.TEXT.value}, '
                                    f'{PgVectorTableSchemeEnums.VECTOR.value}, '
                                    f'{PgVectorTableSchemeEnums.METADATA.value}, '
                                    f'{PgVectorTableSchemeEnums.CHUNK_ID.value}) '
                                    f'VALUES (:text, :vector, :metadata, :chunk_id)')
                    
                    await session.execute(batch_insert_sql, values)

        if create_index:
            await self.create_vector_index(collection_name=collection_name)

        return True
    
    async def search_by_vector(self, collection_name: str, vector: list, limit: int):

        collection_name = _validate_identifier(collection_name)
        safe_limit = max(1, min(int(limit), 200))

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Can not search for records in a non-existed collection: {collection_name}")
            return False
        
        vector = "[" + ",".join([ str(v) for v in vector ]) + "]"
        async with self.db_client() as session:
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

                return [
                    RetrievedDocument(
                        text=record.text,
                        score=record.score,
                        metadata=record.metadata if isinstance(record.metadata, dict) else json.loads(record.metadata or "{}"),
                    )
                    for record in records
                ]

    # ------------------------------------------------------------------
    # N2 — Metadata pre-filter (dense search with JSONB containment)
    # ------------------------------------------------------------------
    async def search_by_vector_filtered(
        self,
        collection_name: str,
        vector: list,
        limit: int,
        metadata_filter: dict | None = None,
    ):
        """Dense vector search with an optional JSONB containment pre-filter.

        When *metadata_filter* is provided (e.g. ``{"asset_id": 7}``), only
        rows whose ``metadata`` column contains all the given key-value pairs
        are considered — equivalent to ``WHERE metadata @> :filter``.  This
        lets callers scope retrieval to a specific file, page-range, etc.
        without loading every candidate.

        Falls back to plain ``search_by_vector`` when no filter is supplied.
        """
        if not metadata_filter:
            return await self.search_by_vector(collection_name, vector, limit)

        collection_name = _validate_identifier(collection_name)
        safe_limit = max(1, min(int(limit), 200))

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(
                f"Can not search (filtered) in non-existed collection: {collection_name}"
            )
            return False

        vec_str = "[" + ",".join(str(v) for v in vector) + "]"
        filter_json = json.dumps(metadata_filter, ensure_ascii=False)

        async with self.db_client() as session:
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

        return [
            RetrievedDocument(
                text=record.text,
                score=record.score,
                metadata=(
                    record.metadata
                    if isinstance(record.metadata, dict)
                    else json.loads(record.metadata or "{}")
                ),
            )
            for record in records
        ]

    # ------------------------------------------------------------------
    # I1 — BM25 / sparse retrieval via PostgreSQL tsvector + ts_rank_cd
    # ------------------------------------------------------------------
    async def search_by_text(
        self,
        collection_name: str,
        query: str,
        limit: int,
        language: str = "simple",
    ):
        """Full-text (sparse) search using PostgreSQL tsvector.

        Uses ``to_tsquery`` with the *simple* dictionary by default so it
        works for any language without requiring a language-specific
        PostgreSQL text-search configuration.  Scores are ``ts_rank_cd``
        values in the [0, 1] range.

        This is the *sparse retrieval leg* of a hybrid dense+sparse pipeline:
        it can surface chunks that embed poorly but contain exact query terms
        — the gap that the regex-recall fallback in RRF cannot fill.

        Enable via ``RAG_ENABLE_BM25=true``.
        """
        collection_name = _validate_identifier(collection_name)
        safe_limit = max(1, min(int(limit), 200))

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(
                f"Can not run text search in non-existed collection: {collection_name}"
            )
            return []

        # Build a tsquery: split on whitespace, join with AND (&).
        # Tokens are prefix-matched (token:*) so partial words still match.
        raw_terms = [t.strip() for t in (query or "").split() if len(t.strip()) >= 2]
        if not raw_terms:
            return []

        # Each term becomes a prefix tsquery token; joined with '&'.
        tsquery_str = " & ".join(f"{t}:*" for t in raw_terms)

        async with self.db_client() as session:
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
                    self.logger.warning(f"BM25 search failed (tsquery={tsquery_str!r}): {exc}")
                    return []

        return [
            RetrievedDocument(
                text=record.text,
                score=float(record.score),
                metadata=(
                    record.metadata
                    if isinstance(record.metadata, dict)
                    else json.loads(record.metadata or "{}")
                ),
            )
            for record in records
        ]

    # ------------------------------------------------------------------
    # Metadata-filtered full-text search (sparse retrieval with JSONB
    # pre-filter).  Mirrors search_by_vector_filtered for the sparse leg.
    # ------------------------------------------------------------------
    async def search_by_text_filtered(
        self,
        collection_name: str,
        query: str,
        limit: int,
        metadata_filter: dict | None = None,
        language: str = "simple",
    ):
        """Full-text (sparse) search with an optional JSONB metadata pre-filter.

        When *metadata_filter* is provided (e.g. ``{"asset_id": 7}``), only
        rows whose ``metadata`` column contains all the given key-value pairs
        are considered — ``WHERE metadata @> :filter::jsonb AND
        to_tsvector(...) @@ to_tsquery(...)``.  This lets callers scope the
        sparse retrieval channel to a specific asset or category without
        post-filtering.

        Falls back to plain ``search_by_text`` when no filter is supplied.
        """
        if not metadata_filter:
            return await self.search_by_text(
                collection_name=collection_name,
                query=query,
                limit=limit,
                language=language,
            )

        collection_name = _validate_identifier(collection_name)
        safe_limit = max(1, min(int(limit), 200))

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(
                f"Can not run filtered text search in non-existed collection: {collection_name}"
            )
            return []

        # Build a tsquery: split on whitespace, join with AND (&).
        # Tokens are prefix-matched (token:*) so partial words still match.
        raw_terms = [t.strip() for t in (query or "").split() if len(t.strip()) >= 2]
        if not raw_terms:
            return []

        tsquery_str = " & ".join(f"{t}:*" for t in raw_terms)
        filter_json = json.dumps(metadata_filter, ensure_ascii=False)

        async with self.db_client() as session:
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
                    self.logger.warning(
                        f"Filtered BM25 search failed (tsquery={tsquery_str!r}): {exc}"
                    )
                    return []

        return [
            RetrievedDocument(
                text=record.text,
                score=float(record.score),
                metadata=(
                    record.metadata
                    if isinstance(record.metadata, dict)
                    else json.loads(record.metadata or "{}")
                ),
            )
            for record in records
        ]

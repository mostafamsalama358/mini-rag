"""stores/vectordb/providers/pgvector/provider.py — PGVectorProvider facade.

Split out of `PGVectorProvider.py` (003 refactor Phase 4b). This class
implements `VectorDBInterface` and holds the insert paths; it delegates
connection/schema DDL to `schema.py` and retrieval queries to `search.py`.

Constructor signature and all public method signatures are unchanged
(frozen provider contract, spec 003 FR-001).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.sql import text as sql_text

from ...VectorDBInterface import VectorDBInterface
from ...VectorDBEnums import (
    DistanceMethodEnums,
    PgVectorTableSchemeEnums,
    PgVectorDistanceMethodEnums,
)
from .schema import (
    _validate_identifier,
    connect as _connect,
    create_collection as _create_collection,
    create_vector_index as _create_vector_index,
    delete_collection as _delete_collection,
    disconnect as _disconnect,
    get_collection_info as _get_collection_info,
    is_collection_existed as _is_collection_existed,
    is_index_existed as _is_index_existed,
    list_all_collections as _list_all_collections,
    reset_vector_index as _reset_vector_index,
)
from .search import (
    search_by_text as _search_by_text,
    search_by_text_field as _search_by_text_field,
    search_by_text_filtered as _search_by_text_filtered,
    search_by_text_scoped as _search_by_text_scoped,
    search_by_vector as _search_by_vector,
    search_by_vector_field as _search_by_vector_field,
    search_by_vector_filtered as _search_by_vector_filtered,
    search_by_vector_scoped as _search_by_vector_scoped,
)


class PGVectorProvider(VectorDBInterface):

    def __init__(self, db_client, default_vector_size: int = 786,
                       distance_method: str = None, index_threshold: int = 100):

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

    # ---- connection / schema (delegate) ----

    async def connect(self):
        await _connect(self.db_client, self.logger)

    async def disconnect(self):
        _disconnect()

    async def is_collection_existed(self, collection_name: str) -> bool:
        return await _is_collection_existed(self.db_client, collection_name)

    async def list_all_collections(self):
        return await _list_all_collections(self.db_client, self.pgvector_table_prefix)

    async def get_collection_info(self, collection_name: str) -> dict:
        return await _get_collection_info(self.db_client, collection_name)

    async def delete_collection(self, collection_name: str):
        return await _delete_collection(self.db_client, self.logger, collection_name)

    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False):
        return await _create_collection(
            self.db_client, self.logger,
            collection_name=collection_name,
            embedding_size=embedding_size,
            do_reset=do_reset,
        )

    async def is_index_existed(self, collection_name: str) -> bool:
        return await _is_index_existed(self.db_client, collection_name)

    async def create_vector_index(self, collection_name: str, index_type=None):
        from ...VectorDBEnums import PgVectorIndexTypeEnums
        if index_type is None:
            index_type = PgVectorIndexTypeEnums.HNSW.value
        return await _create_vector_index(
            self.db_client, self.logger,
            collection_name=collection_name,
            index_threshold=self.index_threshold,
            distance_method=self.distance_method,
            index_type=index_type,
        )

    async def reset_vector_index(self, collection_name: str, index_type=None) -> bool:
        from ...VectorDBEnums import PgVectorIndexTypeEnums
        if index_type is None:
            index_type = PgVectorIndexTypeEnums.HNSW.value
        return await _reset_vector_index(
            self.db_client, self.logger,
            collection_name=collection_name,
            index_threshold=self.index_threshold,
            distance_method=self.distance_method,
            index_type=index_type,
        )

    # ---- search (delegate) ----

    async def search_by_vector(self, collection_name: str, vector: list, limit: int):
        return await _search_by_vector(self.db_client, self.logger, collection_name, vector, limit)

    async def search_by_vector_filtered(self, collection_name: str, vector: list, limit: int, metadata_filter: dict | None = None):
        return await _search_by_vector_filtered(
            self.db_client, self.logger,
            collection_name, vector, limit, metadata_filter=metadata_filter,
        )

    async def search_by_text(self, collection_name: str, query: str, limit: int, language: str = "simple"):
        return await _search_by_text(
            self.db_client, self.logger,
            collection_name, query, limit, language=language,
        )

    async def search_by_text_filtered(self, collection_name: str, query: str, limit: int, metadata_filter: dict | None = None, language: str = "simple"):
        return await _search_by_text_filtered(
            self.db_client, self.logger,
            collection_name, query, limit, metadata_filter=metadata_filter, language=language,
        )

    async def search_by_vector_field(
        self, collection_name: str, vector: list, limit: int,
        field_key: str, field_value: str | None = None,
    ):
        """Dense search restricted to rows where a metadata field is present/
        equals. Generic field-aware primitive — see search.py."""
        return await _search_by_vector_field(
            self.db_client, self.logger,
            collection_name, vector, limit,
            field_key=field_key, field_value=field_value,
        )

    async def search_by_text_field(
        self, collection_name: str, query: str, limit: int,
        field_key: str, field_value: str | None = None, language: str = "simple",
    ):
        """BM25 search restricted to rows where a metadata field is present/
        equals. Generic field-aware primitive — see search.py."""
        return await _search_by_text_field(
            self.db_client, self.logger,
            collection_name, query, limit,
            field_key=field_key, field_value=field_value, language=language,
        )

    async def search_by_vector_scoped(
        self,
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
        return await _search_by_vector_scoped(
            self.db_client,
            self.logger,
            collection_name,
            vector,
            limit,
            entity_key=entity_key,
            entity_prefix=entity_prefix,
            entity_prefixes=entity_prefixes,
            field_key=field_key,
            metadata_filter=metadata_filter,
        )

    async def search_by_text_scoped(
        self,
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
        return await _search_by_text_scoped(
            self.db_client,
            self.logger,
            collection_name,
            query,
            limit,
            entity_key=entity_key,
            entity_prefix=entity_prefix,
            entity_prefixes=entity_prefixes,
            field_key=field_key,
            metadata_filter=metadata_filter,
            language=language,
        )

    # ---- inserts (held in facade) ----

    async def insert_one(self, collection_name: str, text: str, vector: list,
                            metadata: dict = None, record_id: str = None):

        collection_name = _validate_identifier(collection_name)
        existed = await self.is_collection_existed(collection_name=collection_name)
        if not existed:
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
                    'vector': "[" + ",".join([str(v) for v in vector]) + "]",
                    'metadata': metadata_json,
                    'chunk_id': record_id
                })
                await session.commit()

                await self.create_vector_index(collection_name=collection_name)

        return True

    async def get_indexed_chunk_ids(self, collection_name: str) -> set[int]:
        collection_name = _validate_identifier(collection_name)
        existed = await self.is_collection_existed(collection_name=collection_name)
        if not existed:
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
        existed = await self.is_collection_existed(collection_name=collection_name)
        if not existed:
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
                            'vector': "[" + ",".join([str(v) for v in _vector]) + "]",
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

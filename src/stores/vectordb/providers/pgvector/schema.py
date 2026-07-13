"""stores/vectordb/providers/pgvector/schema.py — connection + DDL.

Split out of `PGVectorProvider.py` (003 refactor Phase 4b). Connection setup,
collection/index lifecycle (create/drop/info), and the SQL identifier
allow-list used to safely interpolate table/index names into pgvector SQL.

All functions take the db client and logger explicitly (free functions, no
shared mutable state) so this module has one responsibility: schema DDL.
"""
from __future__ import annotations

import logging
import re
from typing import List

from sqlalchemy.sql import text as sql_text

from ...VectorDBEnums import (
    PgVectorTableSchemeEnums,
    PgVectorIndexTypeEnums,
)

# Identifiers (table/index names) cannot be bound as parameters in pgvector
# SQL, so they are interpolated via f-strings. Validate them against a strict
# allow-list so project-derived names can never become an injection vector.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, field: str = "collection_name") -> str:
    """Allow-list a SQL identifier (table/index name) before interpolation."""
    if not value or not _IDENTIFIER_RE.match(str(value)):
        raise ValueError(f"Invalid {field}: {value!r}")
    return str(value)


def _default_index_name(collection_name: str) -> str:
    return f"{collection_name}_vector_idx"


async def connect(db_client, logger: logging.Logger) -> None:
    async with db_client() as session:
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
            logger.warning(f"Vector extension setup: {str(e)}")
            await session.rollback()


async def disconnect() -> None:
    pass


async def is_collection_existed(db_client, collection_name: str) -> bool:
    record = None
    async with db_client() as session:
        async with session.begin():
            list_tbl = sql_text(f'SELECT * FROM pg_tables WHERE tablename = :collection_name')
            results = await session.execute(list_tbl, {"collection_name": collection_name})
            record = results.scalar_one_or_none()

    return record


async def list_all_collections(db_client, pgvector_table_prefix: str) -> List:
    records = []
    async with db_client() as session:
        async with session.begin():
            list_tbl = sql_text('SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix')
            results = await session.execute(list_tbl, {"prefix": pgvector_table_prefix})
            records = results.scalars().all()

    return records


async def get_collection_info(db_client, collection_name: str) -> dict:
    collection_name = _validate_identifier(collection_name)
    async with db_client() as session:
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


async def delete_collection(db_client, logger: logging.Logger, collection_name: str):
    collection_name = _validate_identifier(collection_name)
    async with db_client() as session:
        async with session.begin():
            logger.info(f"Deleting collection: {collection_name}")

            delete_sql = sql_text(f'DROP TABLE IF EXISTS "{collection_name}"')
            await session.execute(delete_sql)
            await session.commit()

    return True


async def create_collection(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    embedding_size: int,
    do_reset: bool = False,
):
    collection_name = _validate_identifier(collection_name)

    if do_reset:
        _ = await delete_collection(db_client, logger, collection_name=collection_name)

    existed = await is_collection_existed(db_client, collection_name=collection_name)
    if not existed:
        logger.info(f"Creating collection: {collection_name}")
        async with db_client() as session:
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


async def is_index_existed(db_client, collection_name: str) -> bool:
    collection_name = _validate_identifier(collection_name)
    index_name = _default_index_name(collection_name)
    _validate_identifier(index_name, field="index_name")
    async with db_client() as session:
        async with session.begin():
            check_sql = sql_text(f"""
                                SELECT 1
                                FROM pg_indexes
                                WHERE tablename = :collection_name
                                AND indexname = :index_name
                                """)
            results = await session.execute(check_sql, {"index_name": index_name, "collection_name": collection_name})

            return bool(results.scalar_one_or_none())


async def create_vector_index(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    index_threshold: int,
    distance_method: str,
    index_type: str = PgVectorIndexTypeEnums.HNSW.value,
):
    collection_name = _validate_identifier(collection_name)
    index_existed = await is_index_existed(db_client, collection_name=collection_name)
    if index_existed:
        return False

    async with db_client() as session:
        async with session.begin():
            count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
            result = await session.execute(count_sql)
            records_count = result.scalar_one()

            if records_count < index_threshold:
                return False

            logger.info(f"START: Creating vector index for collection: {collection_name}")

            index_name = _default_index_name(collection_name)
            _validate_identifier(index_name, field="index_name")
            create_idx_sql = sql_text(
                                        f'CREATE INDEX "{index_name}" ON "{collection_name}" '
                                        f'USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {distance_method})'
                                      )

            await session.execute(create_idx_sql)

            logger.info(f"END: Created vector index for collection: {collection_name}")


async def reset_vector_index(
    db_client,
    logger: logging.Logger,
    collection_name: str,
    index_threshold: int,
    distance_method: str,
    index_type: str = PgVectorIndexTypeEnums.HNSW.value,
) -> bool:
    collection_name = _validate_identifier(collection_name)
    index_name = _default_index_name(collection_name)
    _validate_identifier(index_name, field="index_name")
    async with db_client() as session:
        async with session.begin():
            drop_sql = sql_text(f'DROP INDEX IF EXISTS "{index_name}"')
            await session.execute(drop_sql)

    return await create_vector_index(
        db_client, logger,
        collection_name=collection_name,
        index_threshold=index_threshold,
        distance_method=distance_method,
        index_type=index_type,
    )

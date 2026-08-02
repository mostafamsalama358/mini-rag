import re
from collections import Counter

from .base import BaseDataModel
from models.db_schemes import DataChunk
from sqlalchemy.future import select
from sqlalchemy import func, delete, text

_METADATA_VALUE_SPLIT = re.compile(r"[*(),;/]+")
_PARENTHETICAL = re.compile(r"\([^)]*\)")


def composition_key(raw: str) -> frozenset[str]:
    """Normalize a compound metadata value into an order-independent ingredient set."""
    cleaned = _PARENTHETICAL.sub(" ", raw or "")
    tokens: set[str] = set()
    for part in _METADATA_VALUE_SPLIT.split(cleaned):
        token = part.strip().upper()
        if len(token) >= 3 and token.replace(" ", "").isalpha():
            tokens.add(token.split()[0])
    return frozenset(tokens)

class ChunkModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_chunk(self, chunk: DataChunk):

        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        return chunk

    async def get_chunk(self, chunk_id: str):

        async with self.db_client() as session:
            # Equivalent to: dbContext.Chunks.Where(c => c.ChunkId == chunkId).FirstOrDefaultAsync()
            result = await session.execute(select(DataChunk).where(DataChunk.chunk_id == chunk_id))
            chunk = result.scalar_one_or_none()
        return chunk

    async def insert_many_chunks(self, chunks: list, batch_size: int=100):
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i:i+batch_size]
                    session.add_all(batch) # Equivalent to dbContext.AddRange(batch)
            await session.commit()
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: int):
        async with self.db_client() as session:
            stmt = delete(DataChunk).where(DataChunk.chunk_project_id == project_id)
            result = await session.execute(stmt)
            await session.commit()
        return result.rowcount

    async def delete_chunks_by_asset_id(self, project_id: int, asset_id: int):
        async with self.db_client() as session:
            stmt = delete(DataChunk).where(
                DataChunk.chunk_project_id == project_id,
                DataChunk.chunk_asset_id == asset_id,
            )
            result = await session.execute(stmt)
            await session.commit()
        return result.rowcount

    async def get_indexed_asset_ids(self, project_id: int) -> set[int]:
        async with self.db_client() as session:
            stmt = select(DataChunk.chunk_asset_id).where(
                DataChunk.chunk_project_id == project_id
            ).distinct()
            result = await session.execute(stmt)
            return {row[0] for row in result.all()}

    async def get_chunks_by_asset(
        self,
        *,
        project_id: int,
        asset_id: int,
    ):
        async with self.db_client() as session:
            stmt = select(DataChunk).where(
                DataChunk.chunk_project_id == project_id,
                DataChunk.chunk_asset_id == asset_id,
            ).order_by(DataChunk.chunk_order)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_chunks_by_asset_page(
        self,
        *,
        project_id: int,
        asset_id: int,
        page: int,
    ):
        async with self.db_client() as session:
            stmt = (
                select(DataChunk)
                .where(
                    DataChunk.chunk_project_id == project_id,
                    DataChunk.chunk_asset_id == asset_id,
                    # jsonb -> 'page' cast to text; coerce the input the same way
                    DataChunk.chunk_metadata["page"].as_string() == str(page),
                )
                .order_by(DataChunk.chunk_order)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_chunks_by_asset_order_range(
        self,
        *,
        project_id: int,
        asset_id: int,
        start_order: int,
        end_order: int,
    ):
        async with self.db_client() as session:
            stmt = select(DataChunk).where(
                DataChunk.chunk_project_id == project_id,
                DataChunk.chunk_asset_id == asset_id,
                DataChunk.chunk_order >= start_order,
                DataChunk.chunk_order <= end_order,
            ).order_by(DataChunk.chunk_order)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_poject_chunks(self, project_id: int, page_no: int=1, page_size: int=50):
        async with self.db_client() as session:
            stmt = (
                select(DataChunk)
                .where(DataChunk.chunk_project_id == project_id)
                .order_by(DataChunk.chunk_id)
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

    async def get_project_chunks_by_offset(
        self,
        project_id: int,
        *,
        offset: int,
        limit: int,
    ):
        async with self.db_client() as session:
            stmt = (
                select(DataChunk)
                .where(DataChunk.chunk_project_id == project_id)
                .order_by(DataChunk.chunk_id)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_total_chunks_count(self, project_id: int):
        total_count = 0
        async with self.db_client() as session:
            count_sql = select(func.count(DataChunk.chunk_id)).where(DataChunk.chunk_project_id == project_id)
            records_count = await session.execute(count_sql)
            total_count = records_count.scalar()

        return total_count

    async def get_chunk_by_asset_order(
        self,
        *,
        project_id: int,
        asset_id: int,
        chunk_order: int,
    ):
        async with self.db_client() as session:
            stmt = select(DataChunk).where(
                DataChunk.chunk_project_id == project_id,
                DataChunk.chunk_asset_id == asset_id,
                DataChunk.chunk_order == chunk_order,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    @staticmethod
    def _safe_metadata_key(key: str) -> bool:
        """Allow JSONB keys with letters, digits, underscore, or space."""
        return bool(key) and all(ch.isalnum() or ch in "_ " for ch in key)

    async def get_distinct_metadata_tokens(
        self,
        project_id: int,
        *,
        metadata_keys: list[str],
    ) -> list[str]:
        """First-token values from the given chunk_metadata keys (distinct, uppercased)."""
        safe_keys = [key for key in metadata_keys if self._safe_metadata_key(key)]
        if not safe_keys:
            return []

        tokens: set[str] = set()
        async with self.db_client() as session:
            for key in safe_keys:
                result = await session.execute(
                    text(
                        """
                        SELECT DISTINCT UPPER(TRIM(SPLIT_PART(chunk_metadata ->> :key, ' ', 1))) AS token
                        FROM chunks
                        WHERE chunk_project_id = :pid
                          AND COALESCE(chunk_metadata ->> :key, '') <> ''
                        """
                    ),
                    {"key": key, "pid": project_id},
                )
                for row in result:
                    token = (row.token or "").strip()
                    if token:
                        tokens.add(token)
        return sorted(tokens)

    async def get_related_metadata_tokens(
        self,
        project_id: int,
        prefix: str,
        *,
        match_key: str,
        value_keys: list[str],
        limit: int = 50,
    ) -> list[str]:
        """Tokens from ``value_keys`` on rows whose ``match_key`` starts with ``prefix``.

        Compound values are split on common separators (* ( ) , ; /).
        """
        prefix_token = (prefix or "").strip()
        if not prefix_token or not self._safe_metadata_key(match_key):
            return []
        safe_value_keys = [key for key in value_keys if self._safe_metadata_key(key)]
        if not safe_value_keys:
            return []

        counts: Counter[str] = Counter()
        async with self.db_client() as session:
            for value_key in safe_value_keys:
                result = await session.execute(
                    text(
                        """
                        SELECT chunk_metadata ->> :value_key AS value
                        FROM chunks
                        WHERE chunk_project_id = :pid
                          AND UPPER(chunk_metadata ->> :match_key) LIKE :prefix
                          AND COALESCE(chunk_metadata ->> :value_key, '') <> ''
                        LIMIT :lim
                        """
                    ),
                    {
                        "pid": project_id,
                        "match_key": match_key,
                        "value_key": value_key,
                        "prefix": f"{prefix_token.upper()}%",
                        "lim": limit,
                    },
                )
                for row in result:
                    raw = (row.value or "").strip()
                    if not raw:
                        continue
                    for part in _METADATA_VALUE_SPLIT.split(raw):
                        token = part.strip().upper()
                        if len(token) >= 4 and token.replace(" ", "").isalpha():
                            counts[token.split()[0]] += 1
        return [token for token, _ in counts.most_common()]

    async def list_transaction_table_rows(
        self,
        project_id: int,
        *,
        limit: int = 5000,
    ) -> list[dict]:
        """Return Excel/CSV table-row chunks for full-file financial audit."""
        sql = """
            SELECT chunk_text, chunk_metadata
            FROM chunks
            WHERE chunk_project_id = :pid
              AND (
                LOWER(COALESCE(chunk_metadata->>'source_type', ''))
                  IN ('xlsx', 'xls', 'csv')
                OR LOWER(COALESCE(chunk_metadata->>'element_type', '')) = 'table-row'
              )
            ORDER BY
              COALESCE(chunk_metadata->>'file_name', ''),
              chunk_id
            LIMIT :lim
        """
        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(
                text(sql), {"pid": project_id, "lim": int(limit)}
            )
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_bylaw_policy_chunks(
        self,
        project_id: int,
        *,
        limit: int = 40,
    ) -> list[dict]:
        """Return internal bylaw / Instructions chunks (exclude large IFRS/COSO noise)."""
        sql = """
            SELECT chunk_text, chunk_metadata
            FROM chunks
            WHERE chunk_project_id = :pid
              AND (
                LOWER(COALESCE(chunk_metadata->>'entity', ''))
                  IN ('internal bylaw', 'audit instructions')
                OR LOWER(COALESCE(chunk_metadata->>'file_name', ''))
                  LIKE ANY (ARRAY['%bylaw%', '%instruction%', '%لايحة%', '%لائحة%'])
              )
            ORDER BY chunk_id
            LIMIT :lim
        """
        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(
                text(sql), {"pid": project_id, "lim": int(limit)}
            )
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_chunks_matching_metadata(
        self,
        project_id: int,
        *,
        value_keys: list[str],
        include_tokens: list[str],
        exclude_key: str | None = None,
        exclude_prefix: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        """Return chunk text/metadata rows matching any include token in value_keys.

        Each item is ``{"text": str, "metadata": dict}``. Optional exclude filters
        out rows whose ``exclude_key`` value starts with ``exclude_prefix``.
        """
        safe_value_keys = [key for key in value_keys if self._safe_metadata_key(key)]
        tokens = [t.strip().upper() for t in include_tokens if t and t.strip()]
        if not safe_value_keys or not tokens:
            return []
        if exclude_key and not self._safe_metadata_key(exclude_key):
            exclude_key = None

        # Build OR clauses for token containment (parameterized).
        token_clauses = []
        params: dict = {"pid": project_id, "lim": limit}
        for index, token in enumerate(tokens):
            tok_param = f"tok_{index}"
            params[tok_param] = f"%{token}%"
            key_parts = []
            for key_index, value_key in enumerate(safe_value_keys):
                vk_param = f"vk_{index}_{key_index}"
                params[vk_param] = value_key
                key_parts.append(
                    f"UPPER(COALESCE(chunk_metadata ->> :{vk_param}, '')) LIKE :{tok_param}"
                )
            token_clauses.append("(" + " OR ".join(key_parts) + ")")

        where_extra = ""
        if exclude_key and exclude_prefix:
            params["exclude_key"] = exclude_key
            params["exclude_prefix"] = f"{exclude_prefix.strip().upper()}%"
            where_extra = (
                " AND UPPER(COALESCE(chunk_metadata ->> :exclude_key, '')) "
                "NOT LIKE :exclude_prefix"
            )

        sql = f"""
            SELECT chunk_text, chunk_metadata
            FROM chunks
            WHERE chunk_project_id = :pid
              AND ({" OR ".join(token_clauses)})
              {where_extra}
            ORDER BY chunk_id
            LIMIT :lim
        """
        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(text(sql), params)
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_chunks_for_entity_prefix(
        self,
        project_id: int,
        *,
        entity_key: str,
        entity_prefix: str,
        limit: int = 500,
    ) -> list[dict]:
        """Return all chunk rows whose ``entity_key`` value starts with ``entity_prefix``."""
        if not self._safe_metadata_key(entity_key):
            return []
        prefix = (entity_prefix or "").strip().upper()
        if not prefix:
            return []

        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(
                text(
                    """
                    SELECT chunk_text, chunk_metadata
                    FROM chunks
                    WHERE chunk_project_id = :pid
                      AND UPPER(chunk_metadata ->> :entity_key) LIKE :prefix
                    ORDER BY chunk_id
                    LIMIT :lim
                    """
                ),
                {
                    "pid": project_id,
                    "entity_key": entity_key,
                    "prefix": f"{prefix}%",
                    "lim": limit,
                },
            )
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_chunks_field_present(
        self,
        project_id: int,
        *,
        field_keys: list[str],
        limit: int = 500,
    ) -> list[dict]:
        """Return rows where ANY of ``field_keys`` is present and non-empty.

        Generic field-presence primitive (no hardcoded column names): the
        caller resolves which column(s) the user asked about via
        core.field_resolution and passes the chunk_metadata keys here. All
        keys are bound as SQL parameters (NFR-007 identifier allow-list
        enforced via _safe_metadata_key).
        """
        safe_keys = [k for k in field_keys if self._safe_metadata_key(k)]
        if not safe_keys:
            return []

        clauses = " OR ".join(
            f"COALESCE(chunk_metadata ->> :k{i}, '') <> ''"
            for i in range(len(safe_keys))
        )
        params: dict = {"pid": project_id, "lim": limit}
        for i, key in enumerate(safe_keys):
            params[f"k{i}"] = key

        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT chunk_text, chunk_metadata
                    FROM chunks
                    WHERE chunk_project_id = :pid
                      AND ({clauses})
                    ORDER BY chunk_id
                    LIMIT :lim
                    """
                ),
                params,
            )
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_chunks_field_matches(
        self,
        project_id: int,
        *,
        field_keys: list[str],
        value: str,
        limit: int = 500,
    ) -> list[dict]:
        """Return rows where ANY ``field_keys`` value equals ``value``.

        Generic field-equality primitive (replaces the hardcoded
        ``col_API1``/``col_API2`` SQL): the column pair is supplied by the
        caller from the pack's interaction_column_pairs rule, so a different
        dataset schema needs no code change.
        """
        safe_keys = [k for k in field_keys if self._safe_metadata_key(k)]
        token = (value or "").strip().upper()
        if not safe_keys or not token:
            return []

        clauses = " OR ".join(
            f"UPPER(COALESCE(chunk_metadata ->> :k{i}, '')) = :tok"
            for i in range(len(safe_keys))
        )
        params: dict = {"pid": project_id, "tok": token, "lim": limit}
        for i, key in enumerate(safe_keys):
            params[f"k{i}"] = key

        rows: list[dict] = []
        async with self.db_client() as session:
            result = await session.execute(
                text(
                    f"""
                    SELECT chunk_text, chunk_metadata
                    FROM chunks
                    WHERE chunk_project_id = :pid
                      AND ({clauses})
                    ORDER BY chunk_id
                    LIMIT :lim
                    """
                ),
                params,
            )
            for row in result:
                rows.append(
                    {
                        "text": row.chunk_text or "",
                        "metadata": dict(row.chunk_metadata or {}),
                    }
                )
        return rows

    async def list_drug_interactions_for_api(
        self,
        project_id: int,
        api_token: str,
        *,
        limit: int = 500,
        column_keys: list[str] | None = None,
    ) -> list[dict]:
        """Return interaction rows matching ``api_token`` on the configured pair.

        Backward-compatible default (col_API1/col_API2) is preserved, but the
        column pair is now a parameter — callers pass the pack-declared
        interaction_column_pairs so a different schema needs no code change.
        """
        keys = column_keys or ["col_API1", "col_API2"]
        return await self.list_chunks_field_matches(
            project_id,
            field_keys=keys,
            value=api_token,
            limit=limit,
        )

    async def list_chunks_matching_compositions(
        self,
        project_id: int,
        *,
        entity_key: str,
        entity_prefix: str,
        material_key: str,
        exclude_entity: bool = True,
        limit: int = 500,
    ) -> list[dict]:
        """Rows whose material composition exactly matches any composition of ``entity_prefix``.

        Composition is compared as an order-independent ingredient set (parenthetical
        synonyms ignored). When ``exclude_entity`` is true, rows of the entity itself
        are omitted.
        """
        if not self._safe_metadata_key(entity_key) or not self._safe_metadata_key(material_key):
            return []
        prefix = (entity_prefix or "").strip().upper()
        if not prefix:
            return []

        target_keys: set[frozenset[str]] = set()
        token_counts: Counter[str] = Counter()
        async with self.db_client() as session:
            entity_rows = await session.execute(
                text(
                    """
                    SELECT chunk_metadata ->> :material_key AS material
                    FROM chunks
                    WHERE chunk_project_id = :pid
                      AND UPPER(chunk_metadata ->> :entity_key) LIKE :prefix
                      AND COALESCE(chunk_metadata ->> :material_key, '') <> ''
                    LIMIT 100
                    """
                ),
                {
                    "pid": project_id,
                    "entity_key": entity_key,
                    "material_key": material_key,
                    "prefix": f"{prefix}%",
                },
            )
            for row in entity_rows:
                key = composition_key(row.material or "")
                if key:
                    target_keys.add(key)
                    token_counts.update(key)

        if not target_keys:
            return []

        # Pre-filter candidates by the most common ingredient, then exact-match sets.
        primary_tokens = [token for token, _ in token_counts.most_common(2)]
        candidates = await self.list_chunks_matching_metadata(
            project_id,
            value_keys=[material_key],
            include_tokens=primary_tokens,
            exclude_key=entity_key if exclude_entity else None,
            exclude_prefix=prefix if exclude_entity else None,
            limit=max(limit * 3, 1000),
        )
        matched: list[dict] = []
        for row in candidates:
            meta = row.get("metadata") or {}
            key = composition_key(str(meta.get(material_key) or ""))
            if key in target_keys:
                matched.append(row)
                if len(matched) >= limit:
                    break
        return matched

    async def get_project_col_metadata_keys(self, project_id: int) -> list[str]:
        """Distinct ``col_*`` keys present in chunk metadata (legacy manifest inference)."""
        async with self.db_client() as session:
            result = await session.execute(
                text(
                    """
                    SELECT DISTINCT key
                    FROM chunks,
                         LATERAL jsonb_object_keys(chunk_metadata) AS key
                    WHERE chunk_project_id = :pid
                      AND key LIKE 'col_%'
                      AND key NOT LIKE 'col__%'
                    ORDER BY key
                    """
                ),
                {"pid": project_id},
            )
            return [row.key for row in result if row.key]

    async def count_entity_prefix_matches(
        self,
        project_id: int,
        *,
        entity_key: str,
        entity_prefix: str,
    ) -> int:
        """Count rows whose entity column starts with ``entity_prefix``."""
        if not self._safe_metadata_key(entity_key):
            return 0
        prefix = (entity_prefix or "").strip().upper()
        if not prefix:
            return 0

        async with self.db_client() as session:
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM chunks
                    WHERE chunk_project_id = :pid
                      AND UPPER(chunk_metadata ->> :entity_key) LIKE :prefix
                    """
                ),
                {
                    "pid": project_id,
                    "entity_key": entity_key,
                    "prefix": f"{prefix}%",
                },
            )
            row = result.fetchone()
            return int(row.cnt or 0) if row is not None else 0

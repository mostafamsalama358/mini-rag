"""Persistence for KnowledgePackage artifacts."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.knowledge.models import KnowledgePackage
from repositories.base import BaseDataModel

logger = logging.getLogger(__name__)


class KnowledgePackageRepository(BaseDataModel):
    """Upsert / fetch KnowledgePackage JSON keyed by (asset_id, extractor_strategy_id)."""

    def __init__(self, db_client: Any) -> None:
        super().__init__(db_client)

    @classmethod
    async def create_instance(cls, db_client: Any) -> "KnowledgePackageRepository":
        return cls(db_client)

    async def save(self, package: KnowledgePackage) -> None:
        payload = package.model_dump(mode="json")
        asset_id = package.metadata.asset_id
        strategy_id = package.metadata.extractor_strategy_id
        package_id = package.metadata.package_id
        async with self.db_client() as session:  # type: ignore[misc]
            session: AsyncSession
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge_packages (
                        package_id, asset_id, extractor_strategy_id, payload
                    ) VALUES (
                        :package_id, :asset_id, :strategy_id, CAST(:payload AS jsonb)
                    )
                    ON CONFLICT (asset_id, extractor_strategy_id)
                    DO UPDATE SET
                        package_id = EXCLUDED.package_id,
                        payload = EXCLUDED.payload
                    """
                ),
                {
                    "package_id": package_id,
                    "asset_id": asset_id,
                    "strategy_id": strategy_id,
                    "payload": json.dumps(payload),
                },
            )
            await session.commit()
            logger.info(
                "knowledge_package_saved package_id=%s asset_id=%s strategy=%s",
                package_id,
                asset_id,
                strategy_id,
            )

    async def get_by_asset(self, asset_id: str) -> KnowledgePackage | None:
        async with self.db_client() as session:  # type: ignore[misc]
            result = await session.execute(
                text(
                    """
                    SELECT payload FROM knowledge_packages
                    WHERE asset_id = :asset_id
                    ORDER BY package_id
                    LIMIT 1
                    """
                ),
                {"asset_id": asset_id},
            )
            row = result.first()
            if row is None:
                return None
            payload = row[0]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return KnowledgePackage.model_validate(payload)

from .base import BaseDataModel
from models.db_schemes import Asset
from models.enums.DataBaseEnum import DataBaseEnum
from sqlalchemy.future import select
from sqlalchemy import update, text
from typing import List

class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_asset(self, asset: Asset):

        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
            await session.commit()
            await session.refresh(asset)
        return asset

    async def get_all_project_assets(self, asset_project_id: str, asset_type: str):

        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_type == asset_type
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

    async def get_asset_record(self, asset_project_id: str, asset_name: str):

        async with self.db_client() as session:
            stmt = select(Asset).where(
                Asset.asset_project_id == asset_project_id,
                Asset.asset_name == asset_name
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
        return record

    async def update_assets_config(self, asset_project_id: str, asset_names: List[str], new_config: dict):
        async with self.db_client() as session:
            async with session.begin():
                stmt = (
                    update(Asset)
                    .where(
                        Asset.asset_project_id == asset_project_id,
                        Asset.asset_name.in_(asset_names)
                    )
                    .values(asset_config=new_config)
                )
                await session.execute(stmt)
            await session.commit()

    async def merge_asset_config_key(self, asset_name: str, *, project_id: int, key: str, value) -> bool:
        """Merge a single key into one asset's asset_config JSONB without
        clobbering sibling keys (PostgreSQL ``||`` shallow merge).

        Used by the indexer to persist the discovered field manifest
        (``asset_config["field_manifest"]``) next to existing config.
        Returns True if a row was updated.
        """
        import json
        async with self.db_client() as session:
            async with session.begin():
                result = await session.execute(
                    text(
                        """
                        UPDATE assets
                        SET asset_config = COALESCE(asset_config, '{}'::jsonb)
                            || jsonb_build_object(
                                CAST(:key AS text),
                                CAST(:value AS jsonb)
                            )
                        WHERE asset_name = :asset_name
                          AND asset_project_id = :pid
                        """
                    ),
                    {
                        "key": key,
                        "value": json.dumps(value, ensure_ascii=False),
                        "asset_name": asset_name,
                        "pid": project_id,
                    },
                )
            await session.commit()
            return (result.rowcount or 0) > 0

    async def get_project_field_manifests(self, project_id: int) -> list[dict]:
        """Return the discovered field_manifest (if any) from every asset in
        a project.

        Used at query time to build a FieldManifest so the generic field
        resolver can map user concepts to concrete chunk_metadata keys.
        Returns a list of {"columns": {...}, "entity_key": str|None} dicts.
        """
        async with self.db_client() as session:
            result = await session.execute(
                text(
                    """
                    SELECT asset_config -> 'field_manifest' AS manifest
                    FROM assets
                    WHERE asset_project_id = :pid
                      AND asset_config ? 'field_manifest'
                    """
                ),
                {"pid": project_id},
            )
            return [
                row.manifest
                for row in result
                if row.manifest and isinstance(row.manifest, dict)
            ]

"""Celery task: run Knowledge Representation for an asset."""

from __future__ import annotations

import logging

from celery_app import celery_app
from core.chunking.models import ChunkSet
from core.knowledge.models import KnowledgePackage
from core.knowledge.pipeline import (
    build_pipeline_from_config,
    load_knowledge_extraction_config,
)

logger = logging.getLogger(__name__)


def run_knowledge_representation_sync(
    chunk_set: ChunkSet,
    *,
    domain: str = "generic",
    project_overrides: dict | None = None,
) -> KnowledgePackage:
    """In-process entrypoint used by workers and tests."""
    config = load_knowledge_extraction_config(
        domain=domain, project_overrides=project_overrides
    )
    pipeline = build_pipeline_from_config(config)
    package = pipeline.run(chunk_set, config)
    logger.info(
        "knowledge_representation_complete asset_id=%s package_id=%s units=%s "
        "relationships=%s extractor=%s normalizer=%s discoverer=%s domain=%s",
        chunk_set.asset_id,
        package.metadata.package_id,
        len(package.knowledge_units),
        len(package.knowledge_relationships),
        package.metadata.extractor_strategy_id,
        package.metadata.normalizer_strategy_id,
        package.metadata.discoverer_strategy_id,
        domain,
    )
    return package


@celery_app.task(name="tasks.knowledge_representation.run_knowledge_representation")
def run_knowledge_representation(
    asset_id: str,
    domain: str = "generic",
    project_id: str = "",
    chunk_set_payload: dict | None = None,
) -> str:
    """Run KR pipeline for an asset.

    MVP accepts an optional serialized ChunkSet payload. Persistence is attempted
    when a DB client factory is available.
    """
    if chunk_set_payload is None:
        raise ValueError(
            f"chunk_set_payload is required for asset_id={asset_id} "
            "(ChunkRepository ChunkSet snapshot loading not yet available)"
        )
    chunk_set = ChunkSet.model_validate(chunk_set_payload)
    package = run_knowledge_representation_sync(chunk_set, domain=domain)

    try:
        from helpers.config import get_settings
        from repositories.knowledge_repository import KnowledgePackageRepository

        settings = get_settings()
        if hasattr(settings, "get_db_client"):
            import asyncio

            async def _persist() -> None:
                repo = await KnowledgePackageRepository.create_instance(
                    settings.get_db_client()
                )
                await repo.save(package)

            asyncio.run(_persist())
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "knowledge_package_persist_skipped asset_id=%s project_id=%s error=%s",
            asset_id,
            project_id,
            exc,
        )

    return package.metadata.package_id

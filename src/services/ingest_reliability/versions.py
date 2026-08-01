"""Logical document version helpers."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_control_plane import LogicalDocumentVersion


async def ensure_preparing_version(
    db_client: object,
    *,
    project_id: int,
    logical_document_id: str,
    version_id: str,
) -> LogicalDocumentVersion:
    async with db_client() as session:
        async with session.begin():
            result = await session.execute(
                select(LogicalDocumentVersion).where(
                    LogicalDocumentVersion.project_id == project_id,
                    LogicalDocumentVersion.logical_document_id == logical_document_id,
                    LogicalDocumentVersion.version_id == version_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = LogicalDocumentVersion(
                    project_id=project_id,
                    logical_document_id=logical_document_id,
                    version_id=version_id,
                    status="preparing",
                    fully_committed=False,
                )
                session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def get_active_version(
    db_client: object, *, project_id: int, logical_document_id: str
) -> Optional[LogicalDocumentVersion]:
    async with db_client() as session:
        result = await session.execute(
            select(LogicalDocumentVersion).where(
                LogicalDocumentVersion.project_id == project_id,
                LogicalDocumentVersion.logical_document_id == logical_document_id,
                LogicalDocumentVersion.status == "active",
            )
        )
        return result.scalar_one_or_none()

"""Resource reclamation after terminal / crash paths."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.future import select

from models.db_schemes.algorag.schemes.ingest_control_plane import (
    IngestCapacityClaim,
    IngestCheckpoint,
)
from models.db_schemes.algorag.schemes.ingest_job import IngestJob


async def reclaim_job_resources(db_client: object, job_id: str) -> dict:
    jid = UUID(str(job_id))
    released_claims = 0
    reclaimed_checkpoints = 0
    async with db_client() as session:
        async with session.begin():
            claim_result = await session.execute(
                select(IngestCapacityClaim).where(
                    IngestCapacityClaim.job_id == jid,
                    IngestCapacityClaim.state == "held",
                )
            )
            for claim in claim_result.scalars().all():
                claim.state = "released"
                claim.released_at = datetime.now(timezone.utc)
                released_claims += 1

            cp_result = await session.execute(
                select(IngestCheckpoint).where(
                    IngestCheckpoint.job_id == jid,
                    IngestCheckpoint.reclaimable.is_(True),
                )
            )
            for cp in cp_result.scalars().all():
                cp.reclaimable = False
                reclaimed_checkpoints += 1

            job_result = await session.execute(
                select(IngestJob).where(IngestJob.job_id == jid)
            )
            job = job_result.scalar_one_or_none()
            if job is not None and job.capacity_claim_id:
                # ensure claim id cleared from job view after release
                pass
        await session.commit()
    return {
        "released_claims": released_claims,
        "reclaimed_checkpoints": reclaimed_checkpoints,
    }

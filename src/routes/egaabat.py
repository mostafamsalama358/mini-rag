"""Egaabat lesson PDF ingest on the existing upload and index path."""

from __future__ import annotations

import logging
import os

import aiofiles
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import delete, update
from sqlalchemy.future import select

from helpers.auth import require_service_api_key
from helpers.config import Settings, get_settings
from models.db_schemes import Asset, Project
from models.enums.AssetTypeEnum import AssetTypeEnum
from models.enums.DomainKeyEnum import DomainKeyEnum
from repositories.asset_repository import AssetModel
from services.project_service import ProjectController

logger = logging.getLogger("uvicorn.error")

egaabat_router = APIRouter(
    prefix="/api/v1/integrations/egaabat",
    tags=["api_v1", "egaabat"],
    dependencies=[Depends(require_service_api_key)],
)


def parse_content_id(content_id: str) -> dict[str, str]:
    parts = (content_id or "").split(":")
    if len(parts) != 5 or parts[0] != "egaabat":
        return {}
    return {
        "grade": parts[1],
        "subject": parts[2],
        "content_type": parts[3],
        "attachment_id": parts[4],
    }


def celery_status(task_id: str | None) -> str:
    if not task_id:
        return "processing"
    from celery.result import AsyncResult
    from celery_app import celery_app

    state = AsyncResult(task_id, app=celery_app).status
    if state == "SUCCESS":
        return "indexed"
    if state in {"FAILURE", "REVOKED"}:
        return "failed"
    return "processing"


def _header(request: Request, name: str) -> str:
    return (request.headers.get(name) or "").strip()


def _document_config(request: Request, content_id: str) -> dict:
    parsed = parse_content_id(content_id)
    grade = _header(request, "x-egaabat-grade") or parsed.get("grade") or ""
    subject = _header(request, "x-egaabat-subject") or parsed.get("subject") or ""
    content_type = _header(request, "x-egaabat-content-type") or parsed.get("content_type") or "textbook"
    attachment_id = _header(request, "x-egaabat-attachment-id") or parsed.get("attachment_id") or ""
    version = _header(request, "x-egaabat-content-version")
    checksum = _header(request, "x-egaabat-checksum-sha256")
    config = {
        "grade": grade,
        "subject": subject,
        "content_id": content_id,
        "content_type": content_type,
        "attachment_id": attachment_id,
        "contentId": content_id,
        "contentType": content_type,
        "attachmentId": attachment_id,
        "classId": grade,
        "subjectId": subject,
    }
    if checksum:
        config["checksum_sha256"] = checksum
        config["checksumSha256"] = checksum
    if version:
        config["content_version"] = version
        config["contentVersion"] = version
    return config


async def _madrsty_project(request: Request) -> Project | None:
    async with request.app.db_client() as session:
        result = await session.execute(
            select(Project).where(Project.domain_key == DomainKeyEnum.MADRSTY)
        )
        return result.scalars().first()


def _asset_name(config: dict) -> str:
    attachment_id = str(config.get("attachment_id") or "document").strip()
    return f"{attachment_id}.pdf"


async def _write_body(request: Request, path: str, max_bytes: int) -> int:
    size = 0
    async with aiofiles.open(path, "wb") as handle:
        async for chunk in request.stream():
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("file_size_exceeded")
            await handle.write(chunk)
    return size


@egaabat_router.put("/content/{content_id:path}")
async def put_content(
    content_id: str,
    request: Request,
    app_settings: Settings = Depends(get_settings),
):
    config = _document_config(request, content_id)
    if not config.get("grade") or not config.get("subject") or not config.get("attachment_id"):
        return JSONResponse(status_code=400, content={"status": "failed", "error": "Missing grade, subject, or attachment id."})

    project = await _madrsty_project(request)
    if project is None:
        return JSONResponse(status_code=404, content={"status": "failed", "error": "Madrsty project was not found."})

    project_dir = ProjectController().get_project_path(project_id=project.project_id)
    asset_name = _asset_name(config)
    file_path = os.path.join(project_dir, asset_name)
    max_bytes = int(app_settings.FILE_MAX_SIZE) * 1024 * 1024

    try:
        size = await _write_body(request, file_path, max_bytes)
    except ValueError:
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse(status_code=413, content={"status": "failed", "error": "file_size_exceeded"})
    except Exception as exc:
        logger.error("Egaabat upload failed: %s", exc)
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse(status_code=400, content={"status": "failed", "error": "file_upload_failed"})

    if size <= 0:
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse(status_code=400, content={"status": "failed", "error": "empty_file"})

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    existing = await asset_model.get_asset_record(
        asset_project_id=project.project_id,
        asset_name=asset_name,
    )
    if existing is None:
        await asset_model.create_asset(
            Asset(
                asset_project_id=project.project_id,
                asset_type=AssetTypeEnum.FILE.value,
                asset_name=asset_name,
                asset_size=size,
                asset_config=config,
            )
        )
    else:
        async with request.app.db_client() as session:
            async with session.begin():
                await session.execute(
                    update(Asset)
                    .where(Asset.asset_id == existing.asset_id)
                    .values(asset_size=size, asset_config=config)
                )

    from celery import chain
    from services.ingest_reliability.admit_flow import admit_ingest_job
    from tasks.file_processing import process_project_files
    from tasks.process_workflow import push_after_process_task

    job, admission_error = await admit_ingest_job(
        request=request,
        project_id=project.project_id,
        file_id=asset_name,
        asset_size_bytes=size,
        settings=app_settings,
    )
    if admission_error is not None and admission_error.status_code != 429:
        return admission_error
    if admission_error is not None:
        return JSONResponse(content={"status": "processing"})

    workflow = chain(
        process_project_files.s(
            project.project_id,
            asset_name,
            app_settings.TEXT_CHUNK_SIZE,
            app_settings.TEXT_CHUNK_OVERLAP,
            0,
        ),
        push_after_process_task.s(project.project_id, 0),
    )
    task = workflow.apply_async()
    if job is not None:
        try:
            from services.ingest_reliability.job_service import IngestJobService

            svc = await IngestJobService.create_instance(request.app.db_client)
            await svc.attach_celery_task(job.job_id, task.id)
        except Exception as exc:
            logger.warning("attach celery task to ingest job failed: %s", exc)

    await asset_model.merge_asset_config_key(
        asset_name,
        project_id=project.project_id,
        key="egaabat_task_id",
        value=task.id,
    )
    return JSONResponse(content={"jobId": task.id, "status": "processing"})


@egaabat_router.get("/content/{content_id:path}")
async def get_content(content_id: str, request: Request):
    project = await _madrsty_project(request)
    if project is None:
        return JSONResponse(status_code=404, content={"status": "failed", "error": "Madrsty project was not found."})

    config = _document_config(request, content_id)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset = await asset_model.get_asset_record(
        asset_project_id=project.project_id,
        asset_name=_asset_name(config),
    )
    if asset is None or not isinstance(asset.asset_config, dict):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    task_id = str(asset.asset_config.get("egaabat_task_id") or "")
    status_name = celery_status(task_id)
    if status_name == "processing":
        from repositories.chunk_repository import ChunkModel

        chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
        indexed_ids = await chunk_model.get_indexed_asset_ids(project.project_id)
        if asset.asset_id in indexed_ids:
            status_name = "indexed"
    body = {"jobId": task_id, "status": status_name}
    if status_name == "failed":
        from celery.result import AsyncResult
        from celery_app import celery_app

        result = AsyncResult(task_id, app=celery_app)
        body["error"] = str(result.result) if result.result else "Task failed"
    return JSONResponse(content=body)


@egaabat_router.delete("/content/{content_id:path}")
async def delete_content(content_id: str, request: Request):
    project = await _madrsty_project(request)
    if project is None:
        return JSONResponse(status_code=404, content={"status": "deleted"})

    config = _document_config(request, content_id)
    asset_name = _asset_name(config)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset = await asset_model.get_asset_record(
        asset_project_id=project.project_id,
        asset_name=asset_name,
    )
    if asset is None:
        return JSONResponse(status_code=404, content={"status": "deleted"})

    from repositories.chunk_repository import ChunkModel
    from tasks.file_processing import _delete_asset_vectors_then_chunks

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    vectordb_client = getattr(request.app, "vectordb_client", None)
    await _delete_asset_vectors_then_chunks(
        vectordb_client,
        chunk_model,
        project_id=project.project_id,
        asset_id=asset.asset_id,
    )

    file_path = os.path.join(ProjectController().get_project_path(project.project_id), asset_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    async with request.app.db_client() as session:
        async with session.begin():
            await session.execute(delete(Asset).where(Asset.asset_id == asset.asset_id))

    return JSONResponse(content={"status": "deleted"})

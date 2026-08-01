from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from celery import chain
from celery.result import AsyncResult
from celery_app import celery_app
import os
from helpers.config import get_settings, Settings
from services.data_service import DataController
from services.project_service import ProjectController
from services.process_service import ProcessController
import aiofiles
from models import ResponseSignal
import logging
from .schemes.data import ProcessRequest, SuggestMetadataRequest, UpdateMetadataRequest
from repositories.project_repository import ProjectModel
from repositories.chunk_repository import ChunkModel
from repositories.asset_repository import AssetModel
from models.db_schemes import DataChunk, Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from services.rag.rag_service import NLPController
from stores.llm.LLMProviderFactory import LLMProviderFactory
from tasks.file_processing import process_project_files
from tasks.process_workflow import push_after_process_task

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)

from fastapi import Form
@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: int, file: UploadFile,
                      metadata: str = Form(None),
                      app_settings: Settings = Depends(get_settings)):
        
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    # validate the file properties
    data_controller = DataController()

    is_valid, result_signal = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": result_signal
            }
        )

    project_dir_path = ProjectController().get_project_path(project_id=project_id)
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_file_name=file.filename,
        project_id=project_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:

        logger.error(f"Error while uploading file: {e}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.FILE_UPLOAD_FAILED.value
            }
        )

    import json
    custom_config = {}
    if metadata:
        try:
            custom_config = json.loads(metadata)
        except json.JSONDecodeError:
            pass

    # store the assets into the database
    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client
    )

    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size=os.path.getsize(file_path),
        asset_config=custom_config
    )

    asset_record = await asset_model.create_asset(asset=asset_resource)

    return JSONResponse(
            content={
                "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
                "asset_name": asset_record.asset_name,
            }
        )



async def _resolve_asset_size_bytes(request: Request, project_id: int, file_id: str | None) -> int:
    if not file_id:
        return 0
    try:
        asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
        asset = await asset_model.get_asset_record(
            asset_project_id=project_id, asset_name=file_id
        )
        if asset is not None:
            return int(asset.asset_size or 0)
    except Exception as exc:
        logger.warning("asset size lookup failed for admission: %s", exc)
    return 0


@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest,
                           app_settings: Settings = Depends(get_settings)):

    chunk_size = process_request.chunk_size or app_settings.TEXT_CHUNK_SIZE
    overlap_size = process_request.overlap_size or app_settings.TEXT_CHUNK_OVERLAP
    do_reset = process_request.do_reset

    from services.ingest_reliability.admit_flow import admit_ingest_job
    from utils.metrics import INGEST_ADMISSION_TOTAL

    size_bytes = await _resolve_asset_size_bytes(
        request, project_id, process_request.file_id
    )
    job, admission_error = await admit_ingest_job(
        request=request,
        project_id=project_id,
        file_id=process_request.file_id,
        asset_size_bytes=size_bytes,
        settings=app_settings,
    )
    if admission_error is not None:
        outcome = "delay" if admission_error.status_code == status.HTTP_429_TOO_MANY_REQUESTS else "reject"
        INGEST_ADMISSION_TOTAL.labels(outcome=outcome, reason="admission").inc()
        return admission_error

    task = process_project_files.delay(
        project_id=project_id,
        file_id=process_request.file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset,
    )

    if job is not None:
        try:
            from services.ingest_reliability.job_service import IngestJobService
            svc = await IngestJobService.create_instance(request.app.db_client)
            await svc.attach_celery_task(job.job_id, task.id)
        except Exception as exc:
            logger.warning("attach celery task to ingest job failed: %s", exc)
        INGEST_ADMISSION_TOTAL.labels(outcome="accept", reason="capacity_available").inc()

    content = {
        "signal": ResponseSignal.PROCESSING_SUCCESS.value,
        "task_id": task.id,
    }
    if job is not None:
        content["job_id"] = str(job.job_id)
        content["correlation_id"] = str(job.correlation_id)
        content["workload_class"] = job.workload_class
        content["lifecycle_state"] = job.lifecycle_state
    return JSONResponse(content=content)

@data_router.post("/process-and-push/{project_id}")
async def process_and_push_endpoint(request: Request, project_id: int, process_request: ProcessRequest,
                                    app_settings: Settings = Depends(get_settings)):

    chunk_size = process_request.chunk_size or app_settings.TEXT_CHUNK_SIZE
    overlap_size = process_request.overlap_size or app_settings.TEXT_CHUNK_OVERLAP
    do_reset = process_request.do_reset

    from services.ingest_reliability.admit_flow import admit_ingest_job
    from utils.metrics import INGEST_ADMISSION_TOTAL

    size_bytes = await _resolve_asset_size_bytes(
        request, project_id, process_request.file_id
    )
    job, admission_error = await admit_ingest_job(
        request=request,
        project_id=project_id,
        file_id=process_request.file_id,
        asset_size_bytes=size_bytes,
        settings=app_settings,
    )
    if admission_error is not None:
        outcome = "delay" if admission_error.status_code == status.HTTP_429_TOO_MANY_REQUESTS else "reject"
        INGEST_ADMISSION_TOTAL.labels(outcome=outcome, reason="admission").inc()
        return admission_error

    workflow = chain(
        process_project_files.s(
            project_id,
            process_request.file_id,
            chunk_size,
            overlap_size,
            do_reset,
        ),
        push_after_process_task.s(project_id, do_reset),
    )
    workflow_result = workflow.apply_async()

    if job is not None:
        try:
            from services.ingest_reliability.job_service import IngestJobService
            svc = await IngestJobService.create_instance(request.app.db_client)
            await svc.attach_celery_task(job.job_id, workflow_result.id)
        except Exception as exc:
            logger.warning("attach celery task to ingest job failed: %s", exc)
        INGEST_ADMISSION_TOTAL.labels(outcome="accept", reason="capacity_available").inc()

    content = {
        "signal": ResponseSignal.PROCESS_AND_PUSH_WORKFLOW_READY.value,
        "task_id": workflow_result.id,
        "workflow_task_id": workflow_result.id,
    }
    if job is not None:
        content["job_id"] = str(job.job_id)
        content["correlation_id"] = str(job.correlation_id)
        content["workload_class"] = job.workload_class
        content["lifecycle_state"] = job.lifecycle_state
    return JSONResponse(content=content)


@data_router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    payload = {
        "signal": ResponseSignal.TASK_STATUS_RETRIEVED.value,
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
    }

    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result) if result.result else "Task failed"

    return JSONResponse(content=payload)


@data_router.get("/ingest-jobs/{job_id}")
async def get_ingest_job(request: Request, job_id: str):
    """Operator-facing ingest job status + recent history (017)."""
    from sqlalchemy.future import select
    from models.db_schemes.algorag.schemes.ingest_control_plane import (
        IngestOperationalEvent,
    )
    from services.ingest_reliability.job_service import IngestJobService

    svc = await IngestJobService.create_instance(request.app.db_client)
    job = await svc.get_by_job_id(job_id)
    if job is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "INGEST_JOB_NOT_FOUND"},
        )
    async with request.app.db_client() as session:
        result = await session.execute(
            select(IngestOperationalEvent)
            .where(IngestOperationalEvent.job_id == job.job_id)
            .order_by(IngestOperationalEvent.recorded_at.desc())
            .limit(50)
        )
        events = [
            {
                "event_type": e.event_type,
                "stage": e.stage,
                "detail": e.detail,
                "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
            }
            for e in result.scalars().all()
        ]
    return JSONResponse(
        content={
            "signal": "INGEST_JOB_STATUS",
            "job_id": str(job.job_id),
            "correlation_id": str(job.correlation_id),
            "lifecycle_state": job.lifecycle_state,
            "workload_class": job.workload_class,
            "progress_stage": job.progress_stage,
            "progress_kind": job.progress_kind,
            "progress_percent": job.progress_percent,
            "parse_outcome": job.parse_outcome,
            "failure_ownership": job.failure_ownership,
            "failure_reason": job.failure_reason,
            "celery_task_id": job.celery_task_id,
            "history": list(reversed(events)),
        }
    )


@data_router.post("/ingest-jobs/{job_id}/cancel")
async def cancel_ingest_job(request: Request, job_id: str):
    from services.ingest_reliability.cancellation import cancel_job

    try:
        await cancel_job(request.app.db_client, job_id, cause="operator_cancel")
    except Exception as exc:
        logger.warning("cancel ingest job failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": "INGEST_JOB_CANCEL_FAILED", "error": str(exc)},
        )
    return JSONResponse(
        content={"signal": "INGEST_JOB_CANCELLED", "job_id": job_id}
    )


@data_router.post("/suggest-metadata/{project_id}")
async def suggest_metadata(request: Request, project_id: int, req_body: SuggestMetadataRequest, app_settings: Settings = Depends(get_settings)):
    try:
        if not req_body.file_names:
            return JSONResponse(content={"tags": []})
            
        generation_client = getattr(request.app, "generation_client", None)
        if not generation_client:
            generation_client = LLMProviderFactory(app_settings).create(provider=app_settings.GENERATION_BACKEND)
        
        file_names_str = ", ".join(req_body.file_names)
        prompt = f"Given the following file names uploaded to a project: {file_names_str}. Suggest up to 5 concise and relevant metadata tags that could be useful for categorizing them. Return ONLY the tags separated by commas. No extra text."
        
        response = generation_client.generate_text(prompt=prompt)
        tags = [tag.strip() for tag in response.split(",") if tag.strip()]
        return JSONResponse(content={"tags": tags[:5]})
    except Exception as e:
        import traceback
        logger.error(f"Error generating metadata: {traceback.format_exc()}")
        return JSONResponse(content={"tags": ["Report", "Document", "Data"]})

@data_router.post("/update-metadata/{project_id}")
async def update_metadata(req: Request, project_id: int, request: UpdateMetadataRequest):
    if not request.file_names or not request.tags:
        return JSONResponse(content={"signal": "NO_UPDATES"})
        
    asset_model = await AssetModel.create_instance(db_client=req.app.db_client)
    
    # get the project numeric id first
    project_model = await ProjectModel.create_instance(db_client=req.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    
    config = {"tags": request.tags}
    await asset_model.update_assets_config(project.project_id, request.file_names, config)
    
    return JSONResponse(content={"signal": "METADATA_UPDATED"})

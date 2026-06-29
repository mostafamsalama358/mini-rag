from fastapi import FastAPI, APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from celery import chain
from celery.result import AsyncResult
from celery_app import celery_app
import os
from helpers.config import get_settings, Settings
from controllers.DataController import DataController
from controllers.ProjectController import ProjectController
from controllers.ProcessController import ProcessController
import aiofiles
from models import ResponseSignal
import logging
from .schemes.data import ProcessRequest, SuggestMetadataRequest, UpdateMetadataRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.db_schemes import DataChunk, Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from controllers.NLPController import NLPController
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



@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: int, process_request: ProcessRequest,
                           app_settings: Settings = Depends(get_settings)):

    chunk_size = process_request.chunk_size or app_settings.TEXT_CHUNK_SIZE
    overlap_size = process_request.overlap_size or app_settings.TEXT_CHUNK_OVERLAP
    do_reset = process_request.do_reset

    task = process_project_files.delay(
        project_id=project_id,
        file_id=process_request.file_id,
        chunk_size=chunk_size,
        overlap_size=overlap_size,
        do_reset=do_reset,
    )

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "task_id": task.id
        }
    )

@data_router.post("/process-and-push/{project_id}")
async def process_and_push_endpoint(request: Request, project_id: int, process_request: ProcessRequest,
                                    app_settings: Settings = Depends(get_settings)):

    chunk_size = process_request.chunk_size or app_settings.TEXT_CHUNK_SIZE
    overlap_size = process_request.overlap_size or app_settings.TEXT_CHUNK_OVERLAP
    do_reset = process_request.do_reset

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

    return JSONResponse(
        content={
            "signal": ResponseSignal.PROCESS_AND_PUSH_WORKFLOW_READY.value,
            "task_id": workflow_result.id,
            "workflow_task_id": workflow_result.id,
        }
    )


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

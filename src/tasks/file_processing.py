from celery_app import celery_app
from celery_runtime import get_db_client, get_setup_utils
from helpers.config import get_settings
import asyncio
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.db_schemes import DataChunk
from models import ResponseSignal
from models.enums.AssetTypeEnum import AssetTypeEnum
from controllers.ProcessController import ProcessController
from controllers.NLPController import NLPController
from utils.idempotency_manager import IdempotencyManager
from utils.chunk_metadata import normalize_chunk_metadata
from utils.project_assets import build_asset_fingerprint

import logging
logger = logging.getLogger(__name__)

@celery_app.task(
                 bind=True, name="tasks.file_processing.process_project_files",
                 autoretry_for=(Exception,),
                 retry_kwargs={'max_retries': 3, 'countdown': 60}
                )
def process_project_files(self, project_id: int, 
                          file_id: int, chunk_size: int,
                          overlap_size: int, do_reset: int):

    return asyncio.run(
        _process_project_files(self, project_id, file_id, chunk_size,
                               overlap_size, do_reset)
    )


async def _process_project_files(task_instance, project_id: int, 
                                 file_id: int, chunk_size: int,
                                 overlap_size: int, do_reset: int):

    
    db_engine, vectordb_client = None, None

    try:
        db_engine, db_client = await get_db_client()
        asset_model = await AssetModel.create_instance(db_client=db_client)
        project_assets = await asset_model.get_all_project_assets(
            asset_project_id=project_id,
            asset_type=AssetTypeEnum.FILE.value,
        )
        asset_fingerprint = build_asset_fingerprint(project_assets)
        await db_engine.dispose()
        db_engine = None
    except Exception:
        asset_fingerprint = "unknown"
        if db_engine:
            await db_engine.dispose()
            db_engine = None

    task_args = {
        "project_id": project_id,
        "file_id": file_id,
        "chunk_size": chunk_size,
        "overlap_size": overlap_size,
        "do_reset": do_reset,
        "asset_fingerprint": asset_fingerprint,
    }
    task_name = "tasks.file_processing.process_project_files"
    settings = get_settings()

    try:
        db_engine, db_client = await get_db_client()
        idempotency_manager = IdempotencyManager(db_client, db_engine)

        should_execute, existing_task = await idempotency_manager.should_execute_task(
            task_name=task_name,
            task_args=task_args,
            celery_task_id=task_instance.request.id,
            task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        )

        if not should_execute:
            logger.info(
                "Skipping duplicate file processing task | status: %s",
                existing_task.status,
            )
            cached = existing_task.result or {}
            return {
                "signal": cached.get("signal", ResponseSignal.PROCESSING_SUCCESS.value),
                "project_id": task_args["project_id"],
                "do_reset": task_args["do_reset"],
                "inserted_chunks": cached.get("inserted_chunks"),
                "processed_files": cached.get("processed_files"),
            }

        await db_engine.dispose()
        db_engine = None

        vectordb_client = None
        if do_reset == 1:
            (db_engine, db_client, llm_provider_factory,
            vectordb_provider_factory,
            generation_client, embedding_client,
            vectordb_client, template_parser) = await get_setup_utils()
        else:
            db_engine, db_client = await get_db_client()

        idempotency_manager = IdempotencyManager(db_client, db_engine)

        task_record = None
        if existing_task:
            await idempotency_manager.update_task_for_retry(
                execution_id=existing_task.execution_id,
                celery_task_id=task_instance.request.id,
            )
            task_record = existing_task
        else:
            # Create new task record
            task_record = await idempotency_manager.create_task_record(
                task_name=task_name,
                task_args=task_args,
                celery_task_id=task_instance.request.id
            )
        
        # Update status to STARTED
        await idempotency_manager.update_task_status(
            execution_id=task_record.execution_id,
            status='STARTED'
        )


        project_model = await ProjectModel.create_instance(
            db_client=db_client
        )

        project = await project_model.get_project_or_create_one(
            project_id=project_id
        )

        nlp_controller = None
        if do_reset == 1:
            nlp_controller = NLPController(
                vectordb_client=vectordb_client,
                generation_client=generation_client,
                embedding_client=embedding_client,
                template_parser=template_parser,
            )

        asset_model = await AssetModel.create_instance(
                db_client=db_client
            )

        project_files_ids = {}
        if file_id:
            asset_record = await asset_model.get_asset_record(
                asset_project_id=project.project_id,
                asset_name=file_id
            )

            if asset_record is None:
                task_instance.update_state(
                    state="FAILURE",
                    meta={
                        "signal": ResponseSignal.FILE_ID_ERROR.value,
                    }
                )

                # Update task status to FAILURE
                await idempotency_manager.update_task_status(
                    execution_id=task_record.execution_id,
                    status='FAILURE',
                    result={"signal": ResponseSignal.FILE_ID_ERROR.value}
                )

                raise Exception(f"No assets for file: {file_id}")

            project_files_ids = {
                asset_record.asset_id: asset_record.asset_name
            }
        
        else:
            

            project_files = await asset_model.get_all_project_assets(
                asset_project_id=project.project_id,
                asset_type=AssetTypeEnum.FILE.value,
            )

            project_files_ids = {
                record.asset_id: record.asset_name
                for record in project_files
            }

        if len(project_files_ids) == 0:

            task_instance.update_state(
                state="FAILURE",
                meta={
                    "signal": ResponseSignal.NO_FILES_ERROR.value,
                }
            )

            # Update task status to FAILURE
            await idempotency_manager.update_task_status(
                execution_id=task_record.execution_id,
                status='FAILURE',
                result={"signal": ResponseSignal.NO_FILES_ERROR.value,}
            )

            raise Exception(f"No files found for project_id: {project.project_id}")
        
        process_controller = ProcessController(project_id=project_id)

        no_records = 0
        no_files = 0

        chunk_model = await ChunkModel.create_instance(
                            db_client=db_client
                        )

        indexed_asset_ids: set[int] = set()
        if do_reset == 0:
            indexed_asset_ids = await chunk_model.get_indexed_asset_ids(
                project_id=project.project_id
            )

        if do_reset == 1:
            # delete associated vectors collection
            collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
            _ = await vectordb_client.delete_collection(collection_name=collection_name)

            # delete associated chunks
            _ = await chunk_model.delete_chunks_by_project_id(
                project_id=project.project_id
            )

        for asset_id, file_id in project_files_ids.items():

            if do_reset == 0 and asset_id in indexed_asset_ids:
                logger.info(
                    "Skipping already processed asset | asset_id=%s file=%s",
                    asset_id,
                    file_id,
                )
                continue

            file_content = process_controller.get_file_content(file_id=file_id)

            if file_content is None:
                logger.error(f"Error while processing file: {file_id}")
                continue

            file_chunks = process_controller.process_file_content(
                file_content=file_content,
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size
            )

            if file_chunks is None or len(file_chunks) == 0:
                
                logger.error(f"No chunks for file_id: {file_id}")
                pass

            file_chunks_records = [
                DataChunk(
                    chunk_text=chunk.page_content,
                    chunk_metadata=normalize_chunk_metadata({
                        **(chunk.metadata or {}),
                        "file_name": file_id,
                        "asset_id": asset_id,
                        "chunk_order": i + 1,
                        "char_count": len(chunk.page_content),
                    }),
                    chunk_order=i+1,
                    chunk_project_id=project.project_id,
                    chunk_asset_id=asset_id
                )
                for i, chunk in enumerate(file_chunks)
            ]

            no_records += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
            no_files += 1

        task_instance.update_state(
            state="SUCCESS",
            meta={
                "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            }
        )

        success_result = {
            "signal": ResponseSignal.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_records,
            "processed_files": no_files,
            "project_id": project_id,
            "do_reset": do_reset,
        }
        await idempotency_manager.update_task_status(
            execution_id=task_record.execution_id,
            status='SUCCESS',
            result=success_result,
        )

        logger.warning(f"inserted_chunks: {no_records}")

        return success_result
    
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise
    finally:
        try:
            if db_engine:
                await db_engine.dispose()
            
            if vectordb_client:
                await vectordb_client.disconnect()
        except Exception as e:
            logger.error(f"Task failed while cleaning: {str(e)}")
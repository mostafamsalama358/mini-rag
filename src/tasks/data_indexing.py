from celery_app import celery_app
from celery_runtime import get_setup_utils
from helpers.config import get_settings
import asyncio
from fastapi.responses import JSONResponse
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers.NLPController import NLPController
from models import ResponseSignal
from stores.llm.LLMEnums import LLMEnums
from tqdm.auto import tqdm

import logging
logger = logging.getLogger(__name__)

@celery_app.task(
                 bind=True, name="tasks.data_indexing.index_data_content",
                 autoretry_for=(Exception,),
                 retry_kwargs={'max_retries': 3, 'countdown': 60}
                )
def index_data_content(self, project_id: int, do_reset: int):

    logger.warning("index_data_content started")
    return asyncio.run(
        _index_data_content(self, project_id, do_reset)
    )

async def _index_data_content(task_instance, project_id: int, do_reset: int):

    if project_id is None:
        raise ValueError("project_id is required for vector indexing")

    db_engine, vectordb_client = None, None

    try:

        (db_engine, db_client, llm_provider_factory, 
        vectordb_provider_factory,
        generation_client, embedding_client,
        vectordb_client, template_parser) = await get_setup_utils()

        logger.warning("Setup utils were loaded!")

        project_model = await ProjectModel.create_instance(
            db_client=db_client
        )

        chunk_model = await ChunkModel.create_instance(
            db_client=db_client
        )

        project = await project_model.get_project_or_create_one(
            project_id=project_id
        )

        if not project:

            task_instance.update_state(
                state="FAILURE",
                meta={
                    "signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value
                }
            )

            raise Exception(f"No project found for project_id: {project_id}")
    
        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        has_records = True
        page_no = 1
        inserted_items_count = 0
        idx = 0

        # create collection if not exists
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)

        _ = await vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=embedding_client.embedding_size,
            do_reset=do_reset,
        )

        indexed_chunk_ids: set[int] = set()
        if do_reset != 1 and hasattr(vectordb_client, "get_indexed_chunk_ids"):
            indexed_chunk_ids = await vectordb_client.get_indexed_chunk_ids(
                collection_name=collection_name
            )

        # setup batching
        total_chunks_count = await chunk_model.get_total_chunks_count(project_id=project.project_id)
        pending_chunks_count = max(0, total_chunks_count - len(indexed_chunk_ids))
        pbar = tqdm(total=pending_chunks_count or total_chunks_count, desc="Vector Indexing", position=0)

        settings = get_settings()
        embedding_batch_delay = (
            settings.VERTEX_EMBEDDING_BATCH_DELAY_SECONDS
            if settings.EMBEDDING_BACKEND == LLMEnums.VERTEX.value
            else 0
        )

        while has_records:
            page_chunks = await chunk_model.get_poject_chunks(
                project_id=project.project_id,
                page_no=page_no,
                page_size=settings.INDEXING_CHUNK_PAGE_SIZE,
            )
            if len(page_chunks):
                page_no += 1
            
            if not page_chunks or len(page_chunks) == 0:
                has_records = False
                break

            if indexed_chunk_ids:
                page_chunks = [
                    chunk for chunk in page_chunks
                    if chunk.chunk_id not in indexed_chunk_ids
                ]
                if not page_chunks:
                    continue

            chunks_ids =  [ c.chunk_id for c in page_chunks ]
            idx += len(page_chunks)
            
            is_inserted = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=page_chunks,
                chunks_ids=chunks_ids,
                defer_index=True
            )

            if not is_inserted:
                

                task_instance.update_state(
                    state="FAILURE",
                    meta={
                        "signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value
                    }
                )

                raise Exception(f"can not insert into vectorDB | project_id: {project_id}")

            pbar.update(len(page_chunks))
            inserted_items_count += len(page_chunks)
            indexed_chunk_ids.update(chunks_ids)

            if embedding_batch_delay > 0 and inserted_items_count < total_chunks_count:
                await asyncio.sleep(embedding_batch_delay)
        
        # Create HNSW index once bulk ingestion finishes
        if hasattr(vectordb_client, "create_vector_index"):
            await vectordb_client.create_vector_index(collection_name=collection_name)

        task_instance.update_state(
            state="SUCCESS",
            meta={
                "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
            }
        )

        return {
                "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
                "inserted_items_count": inserted_items_count
        }

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
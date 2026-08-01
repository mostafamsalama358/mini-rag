from celery import chord, group

from celery_app import celery_app
from celery_runtime import get_setup_utils
from helpers.config import get_settings
import asyncio
from repositories.project_repository import ProjectModel
from repositories.chunk_repository import ChunkModel
from services.rag.rag_service import NLPController
from models import ResponseSignal
from stores.llm.LLMEnums import LLMEnums
from tqdm.auto import tqdm

import logging
logger = logging.getLogger(__name__)


def _shard_offset_range(total_chunks: int, shard_index: int, shard_count: int) -> tuple[int, int]:
    per_shard = (total_chunks + shard_count - 1) // shard_count
    start = shard_index * per_shard
    end = min(start + per_shard, total_chunks)
    return start, end


async def _cleanup_indexing_resources(db_engine, vectordb_client) -> None:
    try:
        if db_engine:
            await db_engine.dispose()
        if vectordb_client:
            await vectordb_client.disconnect()
    except Exception as exc:
        logger.error("Task failed while cleaning: %s", exc)


async def _get_total_chunks_count(project_id: int) -> int:
    db_engine, db_client = None, None
    try:
        db_engine, db_client, *_ = await get_setup_utils()
        chunk_model = await ChunkModel.create_instance(db_client=db_client)
        return await chunk_model.get_total_chunks_count(project_id=project_id)
    finally:
        await _cleanup_indexing_resources(db_engine, None)


async def _prepare_indexing_collection(project_id: int, do_reset: int) -> None:
    db_engine, vectordb_client = None, None
    try:
        (
            db_engine,
            db_client,
            _llm_provider_factory,
            _vectordb_provider_factory,
            generation_client,
            embedding_client,
            vectordb_client,
            template_parser,
        ) = await get_setup_utils()

        project_model = await ProjectModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)
        if not project:
            raise ValueError(f"No project found for project_id: {project_id}")

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        await vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=embedding_client.embedding_size,
            do_reset=do_reset,
        )
    finally:
        await _cleanup_indexing_resources(db_engine, vectordb_client)


async def _run_indexing_job(
    *,
    task_instance,
    project_id: int,
    do_reset: int,
    shard_index: int | None,
    shard_count: int | None,
    finalize_index: bool,
    skip_collection_reset: bool = False,
) -> int:
    if project_id is None:
        raise ValueError("project_id is required for vector indexing")

    db_engine, vectordb_client = None, None

    try:
        (
            db_engine,
            db_client,
            _llm_provider_factory,
            _vectordb_provider_factory,
            generation_client,
            embedding_client,
            vectordb_client,
            template_parser,
        ) = await get_setup_utils()

        project_model = await ProjectModel.create_instance(db_client=db_client)
        chunk_model = await ChunkModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)

        if not project:
            task_instance.update_state(
                state="FAILURE",
                meta={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
            )
            raise Exception(f"No project found for project_id: {project_id}")

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)
        await vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=embedding_client.embedding_size,
            do_reset=False if skip_collection_reset else do_reset,
        )

        indexed_chunk_ids: set[int] = set()
        if do_reset != 1 and hasattr(vectordb_client, "get_indexed_chunk_ids"):
            indexed_chunk_ids = await vectordb_client.get_indexed_chunk_ids(
                collection_name=collection_name
            )

        settings = get_settings()
        total_chunks_count = await chunk_model.get_total_chunks_count(
            project_id=project.project_id
        )

        if shard_index is not None and shard_count is not None:
            start_offset, end_offset = _shard_offset_range(
                total_chunks_count, shard_index, shard_count
            )
            progress_desc = f"Vector Indexing shard {shard_index + 1}/{shard_count}"
        else:
            start_offset, end_offset = 0, total_chunks_count
            progress_desc = "Vector Indexing"

        pbar = tqdm(
            total=max(0, end_offset - start_offset),
            desc=progress_desc,
            position=shard_index or 0,
        )

        embedding_batch_delay = (
            settings.VERTEX_EMBEDDING_BATCH_DELAY_SECONDS
            if settings.EMBEDDING_BACKEND == LLMEnums.VERTEX.value
            else 0
        )

        inserted_items_count = 0
        offset = start_offset

        while offset < end_offset:
            page_size = min(settings.INDEXING_CHUNK_PAGE_SIZE, end_offset - offset)
            page_chunks = await chunk_model.get_project_chunks_by_offset(
                project_id=project.project_id,
                offset=offset,
                limit=page_size,
            )
            if not page_chunks:
                break

            offset += len(page_chunks)

            if indexed_chunk_ids:
                page_chunks = [
                    chunk for chunk in page_chunks
                    if chunk.chunk_id not in indexed_chunk_ids
                ]
                if not page_chunks:
                    continue

            chunks_ids = [chunk.chunk_id for chunk in page_chunks]
            is_inserted = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=page_chunks,
                chunks_ids=chunks_ids,
                defer_index=True,
            )

            if not is_inserted:
                task_instance.update_state(
                    state="FAILURE",
                    meta={"signal": ResponseSignal.INSERT_INTO_VECTORDB_ERROR.value},
                )
                raise Exception(f"can not insert into vectorDB | project_id: {project_id}")

            pbar.update(len(page_chunks))
            inserted_items_count += len(page_chunks)
            indexed_chunk_ids.update(chunks_ids)

            if embedding_batch_delay > 0 and offset < end_offset:
                await asyncio.sleep(embedding_batch_delay)

        if finalize_index and hasattr(vectordb_client, "create_vector_index"):
            await vectordb_client.create_vector_index(collection_name=collection_name)

        return inserted_items_count

    except Exception as exc:
        logger.error("Indexing job failed: %s", exc)
        raise
    finally:
        await _cleanup_indexing_resources(db_engine, vectordb_client)


async def _index_data_content_single(task_instance, project_id: int, do_reset: int) -> dict:
    inserted_items_count = await _run_indexing_job(
        task_instance=task_instance,
        project_id=project_id,
        do_reset=do_reset,
        shard_index=None,
        shard_count=None,
        finalize_index=True,
        skip_collection_reset=False,
    )

    task_instance.update_state(
        state="SUCCESS",
        meta={"signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value},
    )
    return {
        "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
        "inserted_items_count": inserted_items_count,
        "sharded": False,
    }


async def _index_data_content_shard(
    task_instance,
    project_id: int,
    do_reset: int,
    shard_index: int,
    shard_count: int,
) -> dict:
    inserted_items_count = await _run_indexing_job(
        task_instance=task_instance,
        project_id=project_id,
        do_reset=do_reset,
        shard_index=shard_index,
        shard_count=shard_count,
        finalize_index=False,
        skip_collection_reset=True,
    )
    return {
        "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
        "inserted_items_count": inserted_items_count,
        "shard_index": shard_index,
        "shard_count": shard_count,
    }


async def _finalize_vector_index_async(
    project_id: int,
    inserted_items_count: int,
    shard_results: list | None,
) -> dict:
    db_engine, vectordb_client = None, None
    try:
        (
            db_engine,
            db_client,
            _llm_provider_factory,
            _vectordb_provider_factory,
            generation_client,
            embedding_client,
            vectordb_client,
            template_parser,
        ) = await get_setup_utils()

        project_model = await ProjectModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)
        if not project:
            raise ValueError(f"No project found for project_id: {project_id}")

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )
        collection_name = nlp_controller.create_collection_name(project_id=project.project_id)

        if hasattr(vectordb_client, "create_vector_index"):
            await vectordb_client.create_vector_index(collection_name=collection_name)

        return {
            "signal": ResponseSignal.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
            "sharded": True,
            "shard_results": shard_results,
        }
    finally:
        await _cleanup_indexing_resources(db_engine, vectordb_client)


def dispatch_index_data_content(task_instance, project_id: int, do_reset: int):
    logger.warning("index_data_content started")
    settings = get_settings()
    shard_count = max(1, settings.INDEXING_SHARD_COUNT)
    min_chunks = max(1, settings.INDEXING_SHARD_MIN_CHUNKS)

    total_chunks = asyncio.run(_get_total_chunks_count(project_id))
    if total_chunks == 0 or shard_count <= 1 or total_chunks < min_chunks:
        return asyncio.run(_index_data_content_single(task_instance, project_id, do_reset))

    logger.warning(
        "index_data_content sharding: project_id=%s shards=%s chunks=%s",
        project_id,
        shard_count,
        total_chunks,
    )
    # Reset/create once here; shards must NOT reset again (would race/truncate).
    asyncio.run(_prepare_indexing_collection(project_id, do_reset))

    # Never chord_result.get() inside a Celery task — that raises
    # "Never call result.get() within a task!" and leaves a half-built index
    # when the parent retries and truncates again.
    workflow = chord(
        group(
            index_data_content_shard.s(project_id, 0, shard_idx, shard_count)
            for shard_idx in range(shard_count)
        ),
        finalize_vector_index.s(project_id),
    )
    raise task_instance.replace(workflow)


# Backward-compatible alias for workflow tasks.
_index_data_content = dispatch_index_data_content


@celery_app.task(
    bind=True,
    name="tasks.data_indexing.index_data_content",
    # Orchestrator must not autoretry after collection reset — retries truncate
    # mid-flight while shard workers are still inserting.
    autoretry_for=(),
)
def index_data_content(self, project_id: int, do_reset: int):
    return dispatch_index_data_content(self, project_id, do_reset)


@celery_app.task(
    bind=True,
    name="tasks.data_indexing.index_data_content_shard",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def index_data_content_shard(
    self,
    project_id: int,
    do_reset: int,
    shard_index: int,
    shard_count: int,
):
    return asyncio.run(
        _index_data_content_shard(self, project_id, do_reset, shard_index, shard_count)
    )


@celery_app.task(
    bind=True,
    name="tasks.data_indexing.finalize_vector_index",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def finalize_vector_index(self, shard_results, project_id: int):
    inserted_items_count = sum(
        (result or {}).get("inserted_items_count", 0)
        for result in (shard_results or [])
    )
    return asyncio.run(
        _finalize_vector_index_async(project_id, inserted_items_count, shard_results)
    )

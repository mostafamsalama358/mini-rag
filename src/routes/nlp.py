from fastapi import FastAPI, APIRouter, status, Request
from fastapi.responses import JSONResponse
from routes.schemes.nlp import PushRequest, SearchRequest, AnswerRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum
from controllers.NLPController import NLPController
from models import ResponseSignal
from tqdm.auto import tqdm
from tasks.data_indexing import index_data_content

import logging

logger = logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)

@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):

    task = index_data_content.delay(
        project_id=project_id,
        do_reset=push_request.do_reset
    )

    return JSONResponse(
        content={
            "signal": ResponseSignal.DATA_PUSH_TASK_READY.value,
            "task_id": task.id
        }
    )
    

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: int):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker=getattr(request.app, "reranker", None),
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(project=project)

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    chunk_count = await chunk_model.get_total_chunks_count(project_id=project.project_id)
    project_assets = await asset_model.get_all_project_assets(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
    )
    indexed_asset_ids = await chunk_model.get_indexed_asset_ids(project_id=project.project_id)
    asset_count = len(project_assets)
    indexed_asset_count = sum(
        1 for asset in project_assets if asset.asset_id in indexed_asset_ids
    )
    coverage = {
        "chunk_count": chunk_count,
        "asset_count": asset_count,
        "indexed_asset_count": indexed_asset_count,
        "pending_asset_count": max(0, asset_count - indexed_asset_count),
        "is_fully_indexed": asset_count > 0 and indexed_asset_count >= asset_count,
    }

    if collection_info is None:
        return JSONResponse(
            content={
                "signal": ResponseSignal.VECTORDB_COLLECTION_NOT_FOUND.value,
                "collection_info": {
                    "table_info": None,
                    "record_count": 0,
                },
                "coverage": coverage,
            },
        )

    collection_info["coverage"] = coverage

    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info
        }
    )

@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: int, search_request: SearchRequest):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker=getattr(request.app, "reranker", None),
    )

    results = await nlp_controller.search_vector_db_collection(
        project=project,
        text=search_request.text,
        limit=search_request.limit,
        metadata_filter=search_request.metadata_filter,
    )

    if not results:
        return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.VECTORDB_SEARCH_ERROR.value
                }
            )
    
    return JSONResponse(
        content={
            "signal": ResponseSignal.VECTORDB_SEARCH_SUCCESS.value,
            "results": [ result.dict()  for result in results ]
        }
    )

@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, answer_request: AnswerRequest):
    
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )

    project = await project_model.get_project_or_create_one(
        project_id=project_id
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
        reranker=getattr(request.app, "reranker", None),
    )

    answer, full_prompt, chat_history, needs_clarification = await nlp_controller.answer_rag_question(
        project=project,
        query=answer_request.text,
        limit=answer_request.limit,
        session_id=answer_request.session_id,
        db_client=request.app.db_client,
        metadata_filter=answer_request.metadata_filter,
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(project=project)
    has_index = collection_info is not None and collection_info.get("record_count", 0) > 0

    if not answer and not has_index:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.RAG_NO_CONTEXT.value,
                "message": "No indexed documents found for this project. Upload a file and wait for indexing to finish.",
            },
        )

    if not answer:
        return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
                    "message": "Could not generate an answer. Try rephrasing the question or re-indexing the project.",
                }
        )
    
    signal = (
        ResponseSignal.RAG_CLARIFICATION_NEEDED
        if needs_clarification
        else ResponseSignal.RAG_ANSWER_SUCCESS
    )

    return JSONResponse(
        content={
            "signal": signal.value,
            "answer": answer,
            "needs_clarification": needs_clarification,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        }
    )

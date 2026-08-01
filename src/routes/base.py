from fastapi import FastAPI, APIRouter, Depends, Request
from helpers.config import get_settings, Settings
import logging

from services.rag.pipeline import PIPELINE_VERSION

logger = logging.getLogger('uvicorn.error')

base_router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)

@base_router.get("/")
async def welcome(request: Request, app_settings: Settings = Depends(get_settings)):

    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION

    factory = getattr(request.app, "rag_pipeline_factory", None)
    payload = {
        "app_name": app_name,
        "app_version": app_version,
        "rag_pipeline": {
            "mode": getattr(app_settings, "RAG_PIPELINE_MODE", "legacy"),
            "factory_ready": factory is not None,
            "pipeline_version": PIPELINE_VERSION,
        },
    }
    return payload

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from uuid import UUID
import logging

from helpers.auth import get_current_user_id
from services.project_service import ProjectController
from models import ResponseSignal
from repositories.project_repository import ProjectModel
from services.FieldRegistry import get_field_registry
from .schemes.projects import (
    ProjectPatchRequest,
    ProjectPromptUpdateRequest,
)

logger = logging.getLogger('uvicorn.error')

projects_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["api_v1", "projects"],
)


@projects_router.get("")
async def list_projects(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """List projects assigned to the authenticated user.

    Returns only public fields (id, project_id, name).
    domain_key and config_json are internal — not exposed to clients.
    """
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project_controller = ProjectController(project_model=project_model)
    projects = await project_controller.list_projects(user_id=user_id)

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_LIST_SUCCESS.value,
        "projects": projects,
    })


# ------------------------------------------------------------------
# Obsolete endpoints — hidden from Swagger (include_in_schema=False).
# Kept functional for backward compatibility during migration.
# ------------------------------------------------------------------


@projects_router.get(
    "/{project_uuid}",
    include_in_schema=False,
    deprecated=True,
)
async def get_project(
    request: Request,
    project_uuid: UUID,
    user_id: str = Depends(get_current_user_id),
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project_controller = ProjectController(project_model=project_model)

    is_valid, result = await project_controller.get_project(
        project_uuid=project_uuid,
        user_id=user_id,
    )

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": result.value},
        )

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_RETRIEVED_SUCCESS.value,
        "project": project_controller.serialize_project(
            result,
            available_domains=project_controller.field_registry.list_fields(),
        ),
    })


@projects_router.patch(
    "/{project_uuid}",
    include_in_schema=False,
    deprecated=True,
)
async def patch_project_config(
    request: Request,
    project_uuid: UUID,
    payload: ProjectPatchRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Update config_json in DB only. [Obsolete]"""
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project_controller = ProjectController(project_model=project_model)

    is_valid, result = await project_controller.update_project_config(
        project_uuid=project_uuid,
        user_id=user_id,
        config_json=payload.config_json,
    )

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": result.value},
        )

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_CONFIG_UPDATED.value,
        "project": project_controller.serialize_project(result),
    })


@projects_router.get(
    "/{project_uuid}/prompt",
    include_in_schema=False,
    deprecated=True,
)
async def get_project_prompt(
    request: Request,
    project_uuid: UUID,
    user_id: str = Depends(get_current_user_id),
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    prompt = await project_model.get_project_prompt(
        project_uuid=project_uuid,
        user_id=user_id,
    )
    if prompt is None:
        return JSONResponse(content={
            "signal": ResponseSignal.PROJECT_PROMPT_RETRIEVED.value,
            "prompt": {
                "prompt_en": None,
                "prompt_ar": None,
            }
        })

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_PROMPT_RETRIEVED.value,
        "prompt": {
            "prompt_en": prompt.prompt_en,
            "prompt_ar": prompt.prompt_ar,
        }
    })


@projects_router.put(
    "/{project_uuid}/prompt",
    include_in_schema=False,
    deprecated=True,
)
async def update_project_prompt(
    request: Request,
    project_uuid: UUID,
    payload: ProjectPromptUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    prompt = await project_model.update_project_prompt(
        project_uuid=project_uuid,
        user_id=user_id,
        prompt_en=payload.prompt_en,
        prompt_ar=payload.prompt_ar,
    )

    if prompt is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND_ERROR.value},
        )

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_PROMPT_UPDATED.value,
        "prompt": {
            "prompt_en": prompt.prompt_en,
            "prompt_ar": prompt.prompt_ar,
        }
    })

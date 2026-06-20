from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from uuid import UUID
import logging

from helpers.auth import get_current_user_id
from controllers.ProjectController import ProjectController
from models import ResponseSignal
from models.ProjectModel import ProjectModel
from .schemes.projects import ProjectCreateRequest

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
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project_controller = ProjectController(project_model=project_model)
    projects = await project_controller.list_projects(user_id=user_id)

    return JSONResponse(content={
        "signal": ResponseSignal.PROJECT_LIST_SUCCESS.value,
        "projects": projects,
    })


@projects_router.post("")
async def create_project(
    request: Request,
    payload: ProjectCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project_controller = ProjectController(project_model=project_model)

    is_valid, result = await project_controller.create_project(
        name=payload.name,
        user_id=user_id,
    )

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": result.value},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "signal": ResponseSignal.PROJECT_CREATED_SUCCESS.value,
            "project": project_controller.serialize_project(result),
        },
    )


@projects_router.get("/{project_uuid}")
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
        "project": project_controller.serialize_project(result),
    })

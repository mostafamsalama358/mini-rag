from .BaseController import BaseController
from models import ResponseSignal
from models.db_schemes import Project
from models.ProjectModel import ProjectModel
import os


class ProjectController(BaseController):

    def __init__(self, project_model: ProjectModel = None):
        super().__init__()
        self.project_model = project_model

    def get_project_path(self, project_id: str):
        project_dir = os.path.join(
            self.files_dir,
            str(project_id)
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    @staticmethod
    def serialize_project(project: Project) -> dict:
        return {
            "id": str(project.project_uuid),
            "project_id": project.project_id,
            "name": project.project_name,
        }

    async def create_project(self, name: str, user_id: str):
        project_name = name.strip()
        if not project_name:
            return False, ResponseSignal.PROJECT_NAME_REQUIRED

        project = await self.project_model.create_user_project(
            project_name=project_name,
            user_id=user_id,
        )
        self.get_project_path(project_id=project.project_id)
        return True, project

    async def list_projects(self, user_id: str):
        projects = await self.project_model.list_projects_for_user(user_id=user_id)
        return [self.serialize_project(project) for project in projects]

    async def get_project(self, project_uuid, user_id: str):
        project = await self.project_model.get_project_by_uuid_for_user(
            project_uuid=project_uuid,
            user_id=user_id,
        )
        if project is None:
            return False, ResponseSignal.PROJECT_NOT_FOUND_ERROR
        return True, project

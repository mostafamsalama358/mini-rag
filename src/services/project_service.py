from .base import BaseController
from models import ResponseSignal
from models.db_schemes import Project
from repositories.project_repository import ProjectModel
from models.enums.DomainKeyEnum import DomainKeyEnum
from services.FieldRegistry import (
    FieldRegistry,
    _deep_merge,
    get_field_registry,
    validate_config_json_size,
)
import os
import logging

logger = logging.getLogger("uvicorn.error")


class ProjectController(BaseController):

    def __init__(self, project_model: ProjectModel = None, field_registry: FieldRegistry | None = None):
        super().__init__()
        self.project_model = project_model
        self.field_registry = field_registry or get_field_registry()

    def get_project_path(self, project_id: str):
        project_dir = os.path.join(
            self.files_dir,
            str(project_id)
        )

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        return project_dir

    @staticmethod
    def serialize_project(
        project: Project,
        *,
        available_domains: list[dict] | None = None,
        public: bool = False,
        field_registry: FieldRegistry | None = None,
    ) -> dict:
        """Serialize a project for API responses.

        When ``public=True`` (client-facing GET), omit domain_key and config_json
        but include localized welcome messages from the field pack.
        """
        payload = {
            "id": str(project.project_uuid),
            "project_id": project.project_id,
            "name": project.project_name,
        }
        domain_key = DomainKeyEnum.parse(getattr(project, "domain_key", None)).value
        if not public:
            payload["domain_key"] = domain_key
            payload["config_json"] = getattr(project, "config_json", None) or {}
        elif field_registry is not None:
            welcomes = dict(field_registry.get_pack(domain_key).prompts.welcomes)
            if welcomes:
                payload["welcome"] = welcomes
        if available_domains is not None:
            payload["available_domains"] = available_domains
        return payload

    # ------------------------------------------------------------------
    # Auto-seed projects from field packs (runs at startup)
    # ------------------------------------------------------------------

    async def ensure_projects_from_registry(self):
        """Idempotent: create one project per registered field pack if not
        already present. Name comes from domain.yaml label, config from
        project.defaults.yaml, and user assignments from project_users.yaml.

        Also syncs project_users junction rows so edits to
        project_users.yaml are reflected on restart.
        """
        fields = self.field_registry.list_fields()
        for entry in fields:
            domain_key = entry["key"]
            label = entry["label"]
            pack = self.field_registry.get_pack(domain_key)
            existing = await self.project_model.get_project_by_domain_key(domain_key)

            if existing is None:
                # Create the project with pack defaults.
                defaults = self.field_registry.load_project_defaults(domain_key)
                final_config = _deep_merge(defaults, None)
                validate_config_json_size(final_config)

                project = await self.project_model.create_user_project(
                    project_name=label,
                    domain_key=domain_key,
                    config_json=final_config,
                )

                # Sync user assignments into junction table.
                user_ids = self.field_registry.get_domain_user_ids(domain_key)
                await self.project_model.sync_project_users(
                    project_id=project.project_id,
                    user_ids=user_ids,
                )

                # Seed project_prompts from fields/{domain}/prompts/ if shipped.
                if pack.prompts.prompts:
                    try:
                        await self.project_model.seed_project_prompts(
                            project_id=project.project_id,
                            prompt_en=pack.prompts.get("en"),
                            prompt_ar=pack.prompts.get("ar"),
                        )
                    except Exception as exc:
                        logger.warning("Failed to seed prompts for project %s: %s", project.project_id, exc)

                self.get_project_path(project_id=project.project_id)
                logger.info(
                    "Auto-created project '%s' (domain_key=%s, users=%s)",
                    label, domain_key, user_ids,
                )
            else:
                # Sync user assignments from project_users.yaml.
                user_ids = self.field_registry.get_domain_user_ids(domain_key)
                await self.project_model.sync_project_users(
                    project_id=existing.project_id,
                    user_ids=user_ids,
                )
                logger.info(
                    "Synced users for project '%s' (domain_key=%s, users=%s)",
                    existing.project_name, domain_key, user_ids,
                )

    # ------------------------------------------------------------------
    # Client-facing queries
    # ------------------------------------------------------------------

    async def list_projects(self, user_id: str):
        """Return projects assigned to *user_id* via the project_users junction.

        The response is public (no domain_key / config_json).
        """
        projects = await self.project_model.list_projects_for_user(user_id=user_id)
        return [
            self.serialize_project(project, public=True, field_registry=self.field_registry)
            for project in projects
        ]

    async def get_project(self, project_uuid, user_id: str):
        project = await self.project_model.get_project_by_uuid_for_user(
            project_uuid=project_uuid,
            user_id=user_id,
        )
        if project is None:
            return False, ResponseSignal.PROJECT_NOT_FOUND_ERROR
        return True, project

    async def update_project_config(self, project_uuid, user_id: str, config_json: dict | None):
        if config_json is None:
            return False, ResponseSignal.PROJECT_NOT_FOUND_ERROR
        validate_config_json_size(config_json)
        project = await self.project_model.update_project_config(
            project_uuid=project_uuid,
            user_id=user_id,
            config_json=config_json,
        )
        if project is None:
            return False, ResponseSignal.PROJECT_NOT_FOUND_ERROR
        return True, project

from .base import BaseDataModel
from models.db_schemes import Project
from models.db_schemes.algorag.schemes.project_user import ProjectUser
from sqlalchemy.future import select
from sqlalchemy import func, delete, update
from sqlalchemy.orm import selectinload


class ProjectModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)
        self.db_client = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_project(self, project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)
        return project

    async def get_project_or_create_one(self, project_id: int):
        if project_id is None:
            raise ValueError("project_id is required")

        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if project is None:
                    project_rec = Project(project_id=project_id)
                    project = await self.create_project(project=project_rec)
                    return project
                else:
                    return project

    async def get_all_projects(self, page: int=1, page_size: int=10):
        async with self.db_client() as session:
            async with session.begin():
                total_documents = await session.execute(select(
                    func.count(Project.project_id)
                ))
                total_documents = total_documents.scalar_one()
                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1

                query = select(Project).offset((page - 1) * page_size).limit(page_size)
                projects = await session.execute(query).scalars().all()
                return projects, total_pages

    async def create_user_project(
        self,
        project_name: str,
        domain_key: str = "generic",
        config_json: dict | None = None,
    ):
        project = Project(
            project_name=project_name.strip(),
            domain_key=domain_key,
            config_json=config_json or {},
        )
        return await self.create_project(project=project)

    async def get_project_by_domain_key(self, domain_key: str):
        """Return one project row matching a domain_key, or None.

        If multiple rows share a domain_key (legacy/orphan projects), return the
        lowest project_id so startup can proceed.
        """
        async with self.db_client() as session:
            query = (
                select(Project)
                .where(Project.domain_key == domain_key)
                .order_by(Project.project_id.asc())
                .limit(1)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def list_projects_for_user(self, user_id: str):
        """List projects assigned to a user via the project_users junction table."""
        async with self.db_client() as session:
            query = (
                select(Project)
                .join(ProjectUser, ProjectUser.project_id == Project.project_id)
                .where(ProjectUser.user_id == user_id)
                .order_by(Project.project_name.asc())
            )
            result = await session.execute(query)
            return result.scalars().all()

    async def sync_project_users(self, project_id: int, user_ids: list[str]):
        """Replace all junction rows for a project with the given user_ids list.

        Used at startup to sync from project_users.yaml.
        """
        async with self.db_client() as session:
            async with session.begin():
                # Delete existing rows.
                await session.execute(
                    delete(ProjectUser).where(ProjectUser.project_id == project_id)
                )
                # Insert new rows.
                if user_ids:
                    session.add_all([
                        ProjectUser(project_id=project_id, user_id=uid)
                        for uid in user_ids
                    ])

    async def get_project_by_uuid(self, project_uuid):
        """Get a single project by UUID (no user ownership check)."""
        async with self.db_client() as session:
            query = select(Project).where(
                Project.project_uuid == project_uuid,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_project_by_uuid_for_user(self, project_uuid, user_id: str):
        """Get a single project by UUID, checking user assignment via junction table."""
        async with self.db_client() as session:
            query = (
                select(Project)
                .join(ProjectUser, ProjectUser.project_id == Project.project_id)
                .where(
                    Project.project_uuid == project_uuid,
                    ProjectUser.user_id == user_id,
                )
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_project_prompt(self, project_uuid, user_id: str):
        async with self.db_client() as session:
            query = (
                select(Project)
                .join(ProjectUser, ProjectUser.project_id == Project.project_id)
                .where(
                    Project.project_uuid == project_uuid,
                    ProjectUser.user_id == user_id,
                )
            )
            result = await session.execute(query)
            project = result.scalar_one_or_none()
            if not project:
                return None
            
            # Return a dict-like object to match expected interface
            class PromptResult:
                def __init__(self, en, ar):
                    self.prompt_en = en
                    self.prompt_ar = ar
            
            return PromptResult(project.prompt_en, project.prompt_ar)

    async def update_project_prompt(self, project_uuid, user_id: str, prompt_en: str | None, prompt_ar: str | None):
        async with self.db_client() as session:
            async with session.begin():
                query = (
                    select(Project)
                    .join(ProjectUser, ProjectUser.project_id == Project.project_id)
                    .where(
                        Project.project_uuid == project_uuid,
                        ProjectUser.user_id == user_id,
                    )
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if not project:
                    return None

                project.prompt_en = prompt_en
                project.prompt_ar = prompt_ar

            await session.commit()
            
            class PromptResult:
                def __init__(self, en, ar):
                    self.prompt_en = en
                    self.prompt_ar = ar
            
            return PromptResult(project.prompt_en, project.prompt_ar)

    async def update_project_config(
        self,
        project_uuid,
        user_id: str,
        config_json: dict,
    ):
        """PATCH /projects/{uuid} — update config_json snapshot in DB only. [Obsolete]"""
        async with self.db_client() as session:
            async with session.begin():
                query = (
                    select(Project)
                    .join(ProjectUser, ProjectUser.project_id == Project.project_id)
                    .where(
                        Project.project_uuid == project_uuid,
                        ProjectUser.user_id == user_id,
                    )
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if not project:
                    return None
                project.config_json = config_json
            await session.commit()
            await session.refresh(project)
            return project

    async def seed_project_prompts(
        self,
        project_id: int,
        prompt_en: str | None,
        prompt_ar: str | None,
    ):
        """Seed project_prompts from fields/{domain}/prompts/ on create if both
        are provided and no override exists yet (spec FR-006, plan Phase C).
        """
        if not prompt_en and not prompt_ar:
            return None
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(
                    Project.project_id == project_id
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if project is None or (project.prompt_en is not None or project.prompt_ar is not None):
                    class PromptResult:
                        def __init__(self, en, ar):
                            self.prompt_en = en
                            self.prompt_ar = ar
                    return PromptResult(project.prompt_en, project.prompt_ar) if project else None
                
                project.prompt_en = prompt_en
                project.prompt_ar = prompt_ar
            await session.commit()
            
            class PromptResult:
                def __init__(self, en, ar):
                    self.prompt_en = en
                    self.prompt_ar = ar
            return PromptResult(project.prompt_en, project.prompt_ar)

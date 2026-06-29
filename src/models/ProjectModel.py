"""
models/ProjectModel.py — Project Repository
============================================
.NET Equivalent: IProjectRepository + ProjectRepository implementation

This class handles database operations for the `Project` entity (DB table `projects`).
It inherits from `BaseDataModel` to get the DB session factory (`db_client`).
"""
from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum
from sqlalchemy.future import select
from sqlalchemy import func
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
        """
        Equivalent to: dbContext.Projects.Add(project); await dbContext.SaveChangesAsync();
        """
        # async with self.db_client() as session: creates a unit of work.
        # Equivalent to: using var session = new AppDbContext();
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            
            # Commit the transaction
            await session.commit()
            # Refresh the entity from DB to load generated fields (like IDs or defaults)
            await session.refresh(project)
        
        return project

    async def get_project_or_create_one(self, project_id: int):
        if project_id is None:
            raise ValueError("project_id is required")

        async with self.db_client() as session:
            async with session.begin():
                # selectinload() is Eager Loading.
                # Equivalent to: dbContext.Projects.Include(p => p.PromptOverride).Where(p => p.ProjectId == projectId)
                query = select(Project).options(selectinload(Project.prompt_override)).where(Project.project_id == project_id)
                
                # Execute the query and get the first result or null (FirstOrDefaultAsync in LINQ)
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if project is None:
                    project_rec = Project(
                        project_id = project_id
                    )

                    project = await self.create_project(project=project_rec)
                    return project
                else:
                    return project

    async def get_all_projects(self, page: int=1, page_size: int=10):

        async with self.db_client() as session:
            async with session.begin():

                total_documents = await session.execute(select(
                    func.count( Project.project_id )
                ))

                total_documents = total_documents.scalar_one()

                total_pages = total_documents // page_size
                if total_documents % page_size > 0:
                    total_pages += 1

                # Offset and Limit are equivalent to .Skip() and .Take() in LINQ
                query = select(Project).offset((page - 1) * page_size ).limit(page_size)
                projects = await session.execute(query).scalars().all()

                return projects, total_pages

    async def create_user_project(self, project_name: str, user_id: str):
        project = Project(
            project_name=project_name.strip(),
            user_id=user_id,
        )
        return await self.create_project(project=project)

    async def list_projects_for_user(self, user_id: str):
        async with self.db_client() as session:
            # order_by is equivalent to .OrderBy() in LINQ
            query = (
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.project_name.asc())
            )
            result = await session.execute(query)
            # scalars().all() returns a flat list of entities. Equivalent to .ToListAsync()
            return result.scalars().all()

    async def get_project_by_uuid_for_user(self, project_uuid, user_id: str):
        async with self.db_client() as session:
            query = select(Project).options(selectinload(Project.prompt_override)).where(
                Project.project_uuid == project_uuid,
                Project.user_id == user_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_project_prompt(self, project_uuid, user_id: str):
        async with self.db_client() as session:
            query = select(Project).options(selectinload(Project.prompt_override)).where(
                Project.project_uuid == project_uuid,
                Project.user_id == user_id,
            )
            result = await session.execute(query)
            project = result.scalar_one_or_none()
            if not project:
                return None
            return project.prompt_override

    async def update_project_prompt(self, project_uuid, user_id: str, prompt_en: str | None, prompt_ar: str | None):
        from models.db_schemes import ProjectPrompt
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).options(selectinload(Project.prompt_override)).where(
                    Project.project_uuid == project_uuid,
                    Project.user_id == user_id,
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()
                if not project:
                    return None

                if project.prompt_override:
                    project.prompt_override.prompt_en = prompt_en
                    project.prompt_override.prompt_ar = prompt_ar
                else:
                    prompt_override = ProjectPrompt(
                        project_id=project.project_id,
                        prompt_en=prompt_en,
                        prompt_ar=prompt_ar,
                    )
                    session.add(prompt_override)
                    project.prompt_override = prompt_override

            await session.commit()

            query = select(Project).options(selectinload(Project.prompt_override)).where(
                Project.project_uuid == project_uuid,
                Project.user_id == user_id,
            )
            result = await session.execute(query)
            project = result.scalar_one_or_none()
            return project.prompt_override


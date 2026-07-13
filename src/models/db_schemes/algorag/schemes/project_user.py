from .algorag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship


class ProjectUser(SQLAlchemyBase):

    __tablename__ = "project_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(255), nullable=False)

    project = relationship("Project", back_populates="project_users")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
        Index("ix_project_users_user_id", "user_id"),
        Index("ix_project_users_project_id", "project_id"),
    )

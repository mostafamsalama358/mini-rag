from .algorag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

class ProjectPrompt(SQLAlchemyBase):

    __tablename__ = "project_prompts"

    prompt_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, unique=True)
    prompt_en = Column(Text, nullable=True)
    prompt_ar = Column(Text, nullable=True)

    project = relationship("Project", back_populates="prompt_override")

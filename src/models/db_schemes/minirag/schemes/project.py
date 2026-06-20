from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, String, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship

class Project(SQLAlchemyBase):

    __tablename__ = "projects"
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    project_name = Column(String(255), nullable=False, default="")
    user_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index('ix_project_user_id', 'user_id'),
    )

    chunks = relationship("DataChunk", back_populates="project")
    assets = relationship("Asset", back_populates="project")

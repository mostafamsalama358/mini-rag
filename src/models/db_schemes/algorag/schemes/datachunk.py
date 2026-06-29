from .algorag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pydantic import BaseModel
import uuid

class DataChunk(SQLAlchemyBase):

    __tablename__ = "chunks"

    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    chunk_text = Column(String, nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)
    chunk_order = Column(Integer, nullable=False)

    chunk_project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    chunk_asset_id = Column(Integer, ForeignKey("assets.asset_id"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project = relationship("Project", back_populates="chunks")
    asset = relationship("Asset", back_populates="chunks")

    __table_args__ = (
        Index('ix_chunk_project_id', chunk_project_id),
        Index('ix_chunk_asset_id', chunk_asset_id),
        # GIN index accelerates JSONB containment/path predicates, e.g. the
        # page filter used by get_chunks_by_asset_page (created idempotently).
        Index(
            'ix_chunk_metadata_gin',
            chunk_metadata,
            postgresql_using='gin',
            postgresql_where=text("chunk_metadata IS NOT NULL"),
        ),
    )

class RetrievedDocument(BaseModel):
    text: str
    score: float
    metadata: dict | None = None

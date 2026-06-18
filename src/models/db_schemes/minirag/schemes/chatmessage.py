from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Index
import uuid

class ChatMessage(SQLAlchemyBase):

    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)
    message_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    session_id = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    role = Column(String, nullable=False)  # 'user', 'model', 'system'
    content = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_chat_message_session_id', session_id),
        Index('ix_chat_message_project_id', project_id),
    )

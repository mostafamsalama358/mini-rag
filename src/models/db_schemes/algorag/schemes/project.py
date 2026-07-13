from .algorag_base import SQLAlchemyBase
from sqlalchemy import Column, Integer, String, DateTime, Enum, func, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from sqlalchemy.orm import relationship

from models.enums.DomainKeyEnum import DomainKeyEnum


class Project(SQLAlchemyBase):

    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    project_name = Column(String(255), nullable=False, default="")

    # Field registry linkage (spec 002). domain_key selects the field pack;
    # config_json is the project's snapshot of that pack's project.defaults.yaml
    # merged with optional request overrides. Runtime reads DB only — never YAML.
    domain_key = Column(
        Enum(DomainKeyEnum, name="domain_key", values_callable=lambda x: [m.value for m in x]),
        nullable=False,
        default=DomainKeyEnum.GENERIC,
        server_default=DomainKeyEnum.GENERIC.value,
    )
    config_json = Column(JSONB, nullable=False, default=dict, server_default="{}")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index('ix_projects_domain_key', 'domain_key'),
    )

    project_users = relationship("ProjectUser", back_populates="project", cascade="all, delete-orphan")

    chunks = relationship("DataChunk", back_populates="project")
    assets = relationship("Asset", back_populates="project")

    prompt_en = Column(Text, nullable=True)
    prompt_ar = Column(Text, nullable=True)

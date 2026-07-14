"""Answer Generation domain models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0.0"


class CitationReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    citation_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    document_title: str | None = None
    section_title: str | None = None
    page_number: int | None = None
    retrieval_score: float = Field(ge=0.0)


class GroundingFlag(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CapabilityModule(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    priority: int = 0


class ComposedPrompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_message: str
    user_message: str
    has_conflict_disclosure: bool = False
    module_names: list[str] = Field(default_factory=list)


class AnswerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str = Field(min_length=1)
    citations: list[CitationReference] = Field(default_factory=list)
    confidence_note: str | None = None
    conflicts_disclosed: bool = False
    no_answer: bool = False
    grounding_flags: list[GroundingFlag] = Field(default_factory=list)
    plan_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _no_answer_citations_empty(self) -> AnswerResult:
        if self.no_answer and self.citations:
            raise ValueError("citations must be empty when no_answer=True")
        return self

    @model_validator(mode="after")
    def _schema_major_version(self) -> AnswerResult:
        expected_major = SCHEMA_VERSION.split(".", maxsplit=1)[0]
        actual_major = self.schema_version.split(".", maxsplit=1)[0]
        if expected_major != actual_major:
            raise ValueError(
                f"schema_version major {actual_major!r} must match {expected_major!r}"
            )
        return self

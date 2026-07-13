"""
fields/schemas.py — Pydantic models for field pack YAML → typed profiles.

These models validate field pack YAML at load time (spec FR-002 / NFR-005).
Loaded by services/FieldRegistry into immutable FieldPack / FieldProfile views.

Conventions:
  - All patterns (regex) compiled lazily by the consumer; YAML holds raw strings.
  - Profiles are plain data; no provider imports (NFR-003 / constitution V).
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntentRule(BaseModel):
    """A single intent: regex patterns (Arabic + English) that, when matched,
    classify the query into this intent.

    Used by retrieval.yaml → RetrievalProfile.intents.
    Optional ``examples`` feed the embedding fallback when regex misses.
    """

    model_config = ConfigDict(extra="ignore")

    patterns: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    flags: str = "IGNORECASE"
    description: str | None = None

    def compiled(self) -> list["re.Pattern"]:  # type: ignore[name-defined]
        import re

        flag = 0
        for token in (self.flags or "").split("|"):
            token = token.strip()
            if token and hasattr(re, token):
                flag |= getattr(re, token)
        return [re.compile(p, flag) for p in self.patterns]


class IntentFallbackConfig(BaseModel):
    """Optional fallback when no intent regex matches (embedding or LLM)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    method: str = "embedding"  # "embedding" | "llm"
    min_similarity: float = 0.55
    timeout_seconds: float = 1.0
    max_output_tokens: int = 1024
    priority: list[str] = Field(default_factory=list)
    prompt_template: str | None = None


class ElementChunkConfig(BaseModel):
    """Per-element-type chunk grouping behaviour (spec 006 FR-009)."""

    model_config = ConfigDict(extra="ignore")

    group: bool = False
    max_chunk_chars: int | None = None
    metadata_keys: list[str] = Field(default_factory=list)


class ChunkingProfile(BaseModel):
    """Chunking strategy resolved **by file extension** (not per domain).

    `by_extension` selects which *parser* runs per raw format (spec 006 R6).
    `element_mapping` configures how StructuralElements become chunks.
    A missing extension falls back to `default_strategy`.
    """

    model_config = ConfigDict(extra="allow")

    by_extension: dict[str, str] = Field(default_factory=dict)
    default_strategy: str = "character"
    chunk_size: int = 800
    overlap: int = 120
    element_mapping: dict[str, ElementChunkConfig] = Field(default_factory=dict)

    @field_validator("by_extension", mode="before")
    @classmethod
    def _normalize_keys(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized: dict[str, str] = {}
        for key, val in value.items():
            key = str(key)
            if key and not key.startswith("."):
                key = f".{key}"
            normalized[key] = str(val)
        return normalized

    def for_extension(self, file_ext: str) -> str:
        """Return the chunking strategy for a file extension.

        Accepts both ".xlsx" and "xlsx" forms.
        """
        if not file_ext:
            return self.default_strategy
        key = file_ext if file_ext.startswith(".") else f".{file_ext}"
        return self.by_extension.get(key, self.default_strategy)


class FieldConceptProfile(BaseModel):
    """One canonical query concept (a *thing users ask about*, not a column).

    This is the declarative bridge between the query vocabulary and the data
    vocabulary. It holds ONLY synonyms + behaviour hints — never a column
    name. Column discovery happens at index time (see core/field_resolution.py),
    so adding a new concept or a new dataset column never requires a code change.

    Fields:
      concept: canonical id ("strengths", "warnings", "storage", ...).
      synonyms: surface forms (Arabic + English + abbreviations) that signal
                this concept in a user query. Matched against the normalized
                query by core.field_resolution.resolve_query_field.
      output_shape: "list" (answer is a name-only enumeration) or "prose".
      resolves_to_columns: optional canonical column-header hints used by the
                field resolver as a *last resort* when a concept is requested
                but no discovered field is named in the query. These are
                header names (e.g. "Strength"), not col_* keys — discovery
                normalizes both sides before matching.
    """

    model_config = ConfigDict(extra="ignore")

    concept: str
    synonyms: list[str] = Field(default_factory=list)
    output_shape: str = "prose"
    resolves_to_columns: list[str] = Field(default_factory=list)


class FieldRegistryProfile(BaseModel):
    """Top-level view of a pack's `fields.yaml`.

    Holds the concept list + generic relationship rules expressed as data
    (not code): which concept corresponds to the entity-identity field, which
    to a composition field, and which column pairs form an interaction edge.
    `entity_key_hint` / `composition_concept` / `interaction_columns` let the
    pack describe dataset shape without leaking it into Python.

    All fields are optional; generic packs ship an empty profile (no-op).
    """

    model_config = ConfigDict(extra="ignore")

    concepts: list[FieldConceptProfile] = Field(default_factory=list)
    # Concept whose values identify a row (e.g. the drug/product name).
    entity_concept: str | None = None
    # Concept whose values describe the composition (for alternatives matching).
    composition_concept: str | None = None
    # Column headers that form an interaction edge (pair). Data, not code.
    interaction_column_pairs: list[list[str]] = Field(default_factory=list)
    # Optional explicit entity column header override (skips auto-detection).
    entity_key_hint: str | None = None


class RetrievalProfile(BaseModel):
    """Retrieval behaviour: intent classification + exhaustive-mode knobs."""

    model_config = ConfigDict(extra="allow")

    intents: dict[str, IntentRule] = Field(default_factory=dict)
    intent_fallback: IntentFallbackConfig = Field(default_factory=IntentFallbackConfig)
    exhaustive_min_limit: int = 30
    disable_chunk_focus: bool = False
    # Intent names that raise the retrieval window to exhaustive_min_limit.
    wide_retrieval_intents: list[str] = Field(default_factory=list)
    # Field-concept registry (fields.yaml). Generic over all query concepts.
    field_registry: FieldRegistryProfile = Field(default_factory=FieldRegistryProfile)


class StructuralProfile(BaseModel):
    """Structural boundary patterns (legal-heavy; optional elsewhere).

    Generic pack provides empty patterns; pharmacy omits the file.
    """

    model_config = ConfigDict(extra="allow")

    boundaries: list[str] = Field(default_factory=list)
    article_query_patterns: list[str] = Field(default_factory=list)
    chapter_query_patterns: list[str] = Field(default_factory=list)
    min_segment_chars: int = 80


class MetadataProfile(BaseModel):
    """Per-field label formatting + extra metadata keys (research R9)."""

    model_config = ConfigDict(extra="allow")

    label_template: str | None = None
    extra_keys: list[str] = Field(default_factory=list)


class DomainMeta(BaseModel):
    """domain.yaml — pack identity."""

    model_config = ConfigDict(extra="ignore")

    key: str
    label: str = ""
    languages: list[str] = Field(default_factory=lambda: ["en", "ar"])
    description: str | None = None


class ProjectDefaults(BaseModel):
    """project.defaults.yaml — copied into projects.config_json on create.

    Deliberately permissive: the DB snapshot is a free-form JSONB column and
    packs evolve their config keys independently of this model.
    """

    model_config = ConfigDict(extra="allow")

    version: int = 1


class PromptBundle(BaseModel):
    """System prompts (system_{lang}.txt) and chat welcome messages (welcome_{lang}.txt)."""

    model_config = ConfigDict(extra="allow")

    prompts: dict[str, str] = Field(default_factory=dict)
    welcomes: dict[str, str] = Field(default_factory=dict)

    def get(self, language: str) -> str | None:
        if not language:
            return None
        lang = language.lower()[:2]
        return self.prompts.get(lang) or self.prompts.get("en")

    def get_welcome(self, language: str) -> str | None:
        if not language:
            return None
        lang = language.lower()[:2]
        return self.welcomes.get(lang) or self.welcomes.get("en") or self.welcomes.get("ar")


class GroundingConfig(BaseModel):
    """Catalog entity grounding settings from parser.yaml."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    min_score: float = 0.82
    metadata_keys: list[str] = Field(default_factory=list)
    entity_aliases: dict[str, str] = Field(default_factory=dict)


class ParserProfile(BaseModel):
    """parser.yaml — semantic query parser configuration."""

    model_config = ConfigDict(extra="allow")

    version: int = 1
    timeout_seconds: float = 2.0
    max_output_tokens: int = 1024
    temperature: float = 0.0
    document_language: str = "en"
    context_turn_window: int = 4
    prompt: str = ""
    allowed_fields: list[str] = Field(default_factory=list)
    entity_grounding: GroundingConfig = Field(default_factory=GroundingConfig)

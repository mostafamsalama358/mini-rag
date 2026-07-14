# Research: Knowledge Representation

**Feature**: `008-knowledge-representation` | **Date**: 2026-07-13

This document resolves all unknowns identified in the Technical Context during Phase 0.
Every decision below is incorporated into the Phase 1 design artifacts (data-model.md,
contracts/, quickstart.md).

---

## R1 — Immutability Enforcement

**Decision**: Use Pydantic v2 `ConfigDict(frozen=True)` on all published models:
`KnowledgeUnit`, `KnowledgeRelationship`, `EvidenceReference`, `KnowledgePackage`,
`KnowledgeValidationReport`.

**Rationale**: Frozen Pydantic models raise `ValidationError` on any field assignment
after construction, providing runtime enforcement without copy-on-write overhead. This
is the lowest-complexity approach consistent with the existing codebase's Pydantic v2
usage (`src/core/chunking/models.py` uses `model_config = ConfigDict(extra="forbid")`).
Freezing adds immutability on top of the existing pattern.

**Alternative considered — explicit `__setattr__` override**: More boilerplate; rejected
since Pydantic v2 already provides this via `frozen=True`.

**Alternative considered — runtime version counters (copy-on-write)**: Unnecessarily
complex for a pipeline that produces units once and never updates them in-place; rejected.

**Test coverage**: `test_models.py` must verify that assigning to any field of a
published `KnowledgeUnit`, `KnowledgeRelationship`, or `KnowledgePackage` raises an
exception (SC-011).

---

## R2 — Deterministic ID Schemes

**Decision**: All ids are derived as `SHA256(canonical_payload)[:16]` with a type prefix.

| Entity | Prefix | Canonical Payload |
|--------|--------|-------------------|
| `EvidenceReference` | `er_` | `"{sorted(chunk_ids)}|{sorted(element_ids)}|{document_model_id}|{asset_id}"` |
| `KnowledgeUnit` | `ku_` | `"{sorted(evidence_ref_ids)}|{type}|{strategy_id}|{config_hash}"` |
| `KnowledgeRelationship` | `kr_` | `"{source_unit_id}|{target_unit_id}|{relationship_type}|{strategy_id}"` |

**Rationale**: Follows the `chunk_id` convention established in `007` (`"ck_" + SHA256[:16]`),
ensuring consistent identity semantics across the pipeline. Using sorted inputs guarantees
stability regardless of collection order (FR-008).

**Alternative considered — UUID4**: Non-deterministic; breaks idempotency (FR-019); rejected.

**Alternative considered — sequential counters**: Not stable across re-runs; rejected.

---

## R3 — Default Knowledge Unit Extraction Strategy (StructuralKnowledgeUnitExtractor)

**Decision**: The default extractor maps Chunk `element_type` (from `StructuralContext`)
to a `KnowledgeUnitType` using the following priority-ordered rules:

| Rule | Trigger | KU Type Assigned |
|------|---------|-----------------|
| 1. Procedural pattern | Numbered steps in chunk text (`^\d+\.` or `^Step \d+`) | `procedure` |
| 2. Definition pattern | Chunk text matches `\b(is defined as|means|refers to|is the)\b` | `definition` |
| 3. Measurement pattern | Chunk text contains a numeric value followed by a unit token (regex) | `measurement` |
| 4. Table element | `element_type` in `{"table", "table-row"}` | `table` |
| 5. List element | `element_type` in `{"list", "list-item"}` | `list` |
| 6. Code/Quote element | `element_type` in `{"code-block", "quote"}` | `structured_observation` |
| 7. Figure placeholder | `element_type == "figure-placeholder"` | `structured_observation` |
| 8. Heading | `element_type == "heading"` | `assertion` |
| 9. Default fallback | any other type | `fact` |

Rules are applied in order; the first match wins. Each extractor produces exactly one
`KnowledgeUnit` per input `Chunk`. A chunk with ambiguous content falls back to `fact`.
Semantic content is set to `{"text": chunk.text, "element_type": chunk.structural_context.element_type}`.

**Rationale**: Structure-based typing is deterministic, requires no LLM inference (FR-022),
and maps directly to the chunk's existing `StructuralContext` (already computed by `007`).
Text-pattern rules for `procedure`, `definition`, and `measurement` are rule-based regexes,
not ML models.

**Alternative considered — LLM-based typing**: Rejected as default (FR-022); permissible
as an optional strategy registered under the same interface.

**Alternative considered — One-to-many extraction (multiple KUs per chunk)**: Supported by
the interface contract (a strategy may return any number of KUs per chunk); however, the
default implementation produces exactly one per chunk for simplicity and determinism. Future
strategies may produce multiple KUs from a single chunk.

---

## R4 — Default Knowledge Normalization Strategy (RuleBasedKnowledgeNormalizer)

**Decision**: Three-pass deterministic normalization:

1. **Surface normalization**: For each KU, compute a normalized key from `semantic_content["text"]`:
   lowercase, strip leading/trailing whitespace, collapse internal whitespace, remove punctuation.

2. **Alias resolution**: Check the normalized key against a domain alias dictionary loaded
   from the active field pack YAML (`knowledge_normalization.alias_map` key, following the
   generic < domain < project precedence of `002-field-registry`). If a match is found,
   replace `semantic_content["canonical_form"]` with the canonical alias target; preserve
   the original as `attributes["aliases"]`.

3. **Duplicate detection**: Group KUs by their normalized key after alias resolution.
   Within each group, merge all KUs with the same normalized key into one canonical KU whose
   `evidence_references` is the union of all input `evidence_references`. The merged unit
   inherits the `type` and `semantic_content` of the first unit in the group (insertion order).
   Merged units that are removed from the set are not included in the output.

**Rationale**: Exact-match normalization on a lowercased+stripped text key is deterministic
and reproducible (FR-023b). It correctly handles surface-form variants like whitespace
differences and case variations. Alias resolution via pack YAML follows the existing
field-registry pattern (FR-002). Near-exact matching (Levenshtein threshold) is reserved
for an optional embedding-assisted strategy.

**Alternative considered — Levenshtein edit-distance deduplication**: Non-deterministic in
grouping order; requires a threshold parameter that is domain-dependent; reserved for an
optional alternative strategy.

**Alternative considered — Embedding cosine similarity**: Downstream concern (FR-003, FR-023b);
rejected as default.

---

## R5 — Default Relationship Discovery Strategy (StructuralRelationshipDiscoverer)

**Decision**: Two-stage sub-pipeline with structural candidate generation and then validation.

**Sub-stage 1 — Candidate generation** produces `RelationshipCandidate` entities for:

| Pattern | Relationship Type | Source | Target | EvidenceRef |
|---------|------------------|--------|--------|-------------|
| Adjacent KUs (prev/next in normalized order) | `sequence` | KU at position i | KU at position i+1 | EvidenceRefs from both |
| Parent/child chunk relationship (from `ChunkRelationships`) | `containment` | parent KU | child KU | EvidenceRef from parent |
| KU under same heading path → first KU in section | `elaboration` | section-head KU | content KU | EvidenceRef from both |

**Sub-stage 2 — Candidate validation** filters candidates where:
- `source_unit_id` or `target_unit_id` not present in the Normalized KU set → dropped,
  logged as dangling reference.
- Self-referencing relationship (`source == target`) → dropped.
- `sequence` relationship producing a cycle → dropped (linear order constraint).

**Rationale**: Structural relationship discovery is fully deterministic, O(n) in number of
KUs, and uses only the structural metadata already present on `Chunk` objects from `007`
(no NLP, no LLM, no embeddings). This satisfies FR-022, SC-007, and SC-008 latency.

**Alternative considered — Co-reference and co-occurrence**: Requires text analysis; reserved
for an optional NLP-based strategy.

**SC-012 testability**: The candidate set must contain at least one candidate that does not
survive validation (the validator test fixture must include a dangling-reference candidate).

---

## R6 — KnowledgePackage Persistence

**Decision**: The `KnowledgePackage` is serialized to JSON via
`knowledge_package.model_dump(mode="json")` and stored in a new `knowledge_packages` DB
table (via `KnowledgePackageRepository`, following the `repositories/base.py` pattern).
The primary key is `(asset_id, strategy_id)`. Re-processing the same asset produces a
new row (or upsert), consistent with the idempotency requirement (FR-019).

The Celery task (`tasks/knowledge_representation.py`) invokes the pipeline, persists the
result via the repository, and emits structured logs. It does not expose the KP directly
via an HTTP route in MVP; downstream components query the repository.

**Alternative considered — File-system storage (JSON file per asset)**: Simpler for MVP
but inconsistent with the existing `chunk_repository.py` DB-backed pattern; rejected for
architectural consistency.

**Alternative considered — Keeping KP in memory only**: Violates observability and
downstream consumption requirements; rejected.

---

## R7 — Latency Budget (SC-008)

**Decision**: KR processing time ≤ **2× chunking stage wall time** for the same ChunkSet
on the same host, measured on a 50-chunk fixture (approximately 40,000 characters total).

**Rationale**:
- Default extraction: O(n) — one regex pass per chunk.
- Default normalization: O(n) — one dict lookup per KU.
- Default discovery candidates: O(n) — one pass for sequence, one for containment.
- Default discovery validation: O(n) — one lookup per candidate.
- Assembly and validation: O(n).

Combined: O(5n) with small constants → fits comfortably within a 2× budget over the chunking
stage (which itself is O(n) with more expensive BoundaryFeatures computation per element pair).

The 2× ratio will be recorded as a baseline in `tests/integration/test_knowledge_pipeline_e2e.py`
(skipped in CI by default, run with `--benchmark` flag).

---

## R8 — `semantic_content` Representation per KU Type

**Decision**: `semantic_content` is a `dict[str, Any]` whose keys depend on the KU type:

| KU Type | `semantic_content` keys |
|---------|------------------------|
| `fact`, `assertion` | `{"text": str}` |
| `definition` | `{"term": str, "definition": str}` (split at first definition keyword; falls back to `{"text": str}` if not parseable) |
| `measurement` | `{"value": str, "unit": str, "context": str}` (split via regex; falls back to `{"text": str}`) |
| `procedure` | `{"steps": list[str]}` (split at numbered lines; falls back to `{"text": str}`) |
| `list` | `{"items": list[str]}` (split at list markers; falls back to `{"text": str}`) |
| `table` | `{"rows": list[dict]}` (from metadata if available; falls back to `{"text": str}`) |
| `structured_observation` | `{"text": str, "element_type": str}` |

**Rationale**: Typed `semantic_content` makes Knowledge Units independently queryable and
machine-readable without NLP. Fallback to `{"text": str}` for any parse failure ensures
no content is silently dropped (spec edge case: chunk with no clear structure).

---

## R9 — `participants` and `attributes` Defaults

**Decision**:
- `participants` defaults to `None` (absent) for `fact`, `list`, `table`,
  `structured_observation`. For `definition`, `participants` is `{"subject": term}`.
  For `procedure`, `participants` is `{"agent": None}` (agent unknown without NLP).
- `attributes` is a `dict[str, Any]` with at minimum `{"source_surface_form": str}` (the
  original chunk text, for auditability). For merged/normalized units, aliases from
  normalization are added as `{"aliases": list[str]}`.

---

## Summary of All Decisions

| Decision | Choice | Gate |
|----------|--------|------|
| Immutability | Pydantic v2 `frozen=True` | FR-008a, FR-009a, FR-017a |
| ID scheme | `{prefix}_{SHA256(payload)[:16]}` | FR-008, FR-019 |
| Default extractor | `StructuralKnowledgeUnitExtractor` (regex + element_type) | FR-022, SC-007 |
| Default normalizer | `RuleBasedKnowledgeNormalizer` (exact-match + alias dict) | FR-023b |
| Default discoverer | `StructuralRelationshipDiscoverer` (seq + containment + elaboration) | FR-023f, SC-007 |
| KP persistence | `knowledge_packages` DB table via `KnowledgePackageRepository` | FR-026 |
| Latency budget | ≤ 2× chunking wall time on 50-chunk fixture | SC-008 |
| `semantic_content` shape | Typed dict per KU type with `{"text": str}` fallback | FR-006 |

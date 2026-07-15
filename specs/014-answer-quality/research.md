# Research: Answer Quality (spec 014)

**Date**: 2026-07-15 | **Phase**: 0 (pre-design)

---

## R-01: EvidencePack Structure — Coverage Evaluator Input Key

**Question**: What fields does `EvidencePack` expose, and which field should
`ICoverageEvaluator` use to match against `GoldenTestFixture.expected_source_ids`?

**Finding**: `src/core/evidence_orchestrator/models.py` defines:

```python
class EvidenceItem(BaseModel):
    item_id: str          # "ei_" + sha16(chunk_id|doc_id)
    doc_id: str           # stable document identifier
    chunk_id: str         # chunk identifier within document
    text: str             # the retrieved chunk text
    relevance_score: float
    citation: Citation    # metadata: document_title, section_title, page_number, etc.
    entity_tags: list[str]
    sources: list[EvidenceItemSource]
    ...

class EvidencePack(BaseModel):
    pack_id: str          # "ep_" prefixed
    plan_id: str          # threaded from RetrievalPlan
    items: list[EvidenceItem]
    is_empty: bool
    ...
```

**Decision**: `GoldenTestFixture.expected_source_ids` entries are matched against
`{item.doc_id for item in evidence_pack.items}`. Rationale:

- `doc_id` is stable and human-readable — golden fixture authors reference documents,
  not internal chunk or item IDs.
- `chunk_id` and `item_id` are internal system identifiers; fixtures authored by
  humans cannot reasonably track chunk-level IDs.
- Coverage means "did retrieval surface this document?" not "did it surface this
  exact chunk?".

A golden fixture entry `expected_source_ids: ["doc-aspirin-pil"]` passes if any
`EvidenceItem` in the pack has `doc_id == "doc-aspirin-pil"`.

**Alternatives considered**:
- Match on `chunk_id`: rejected — too fine-grained; humans cannot maintain chunk IDs
  as documents are re-chunked.
- Match on `item_id`: rejected — `ei_` prefixes are deterministic hashes; same
  problem as chunk_id.

---

## R-02: AnswerResult Structure — Faithfulness and Completeness Inputs

**Question**: What fields does `AnswerResult` expose, and is `plan_id` present
(resolving the spec 014 NFR-004 threading requirement)?

**Finding**: `src/core/answer_generation/models.py` confirms:

```python
class AnswerResult(BaseModel):
    answer: str
    citations: list[CitationReference]
    confidence_note: str | None
    conflicts_disclosed: bool
    no_answer: bool
    grounding_flags: list[GroundingFlag]
    plan_id: str          # ← confirmed present, Field(min_length=1)
    context_id: str       # ← confirmed present
    schema_version: str
```

`CitationReference` carries `citation_id`, `document_id`, `chunk_id`,
`document_title`, `section_title`, `page_number`, `retrieval_score`.

**Decision**: NFR-004 and `GoldenTestResult.plan_id` in spec 014 are correct.
`plan_id` is threaded from `Context.plan_id` → `AnswerResult.plan_id` → `GoldenTestResult.plan_id`
using `answer_result.plan_id` directly. No spec change needed.

---

## R-03: Faithfulness Text Corpus — Citations vs ContextBlocks

**Question**: For text-based faithfulness checking, should the scorer compare answer
claims against `Context.citation_map` values (Citation objects) or
`Context.ordered_blocks[*].text`?

**Finding**: `Citation` (from `core.evidence_orchestrator.models`) carries only
metadata: `document_id`, `chunk_id`, `retrieval_score`, `score_source`, `page_number`,
`section_title`, `document_title`, `chunk_index`. **It does not carry chunk text.**

`ContextBlock` (from `core.context_builder.models`) carries `item_id`, `document_id`,
`text`, `token_count`, `compressed`, `section_path`. The `text` field contains the
actual retrieved chunk text shown to the LLM.

**Decision**: `IFaithfulnessScorer.score()` builds its ground-truth text corpus from
`Context.ordered_blocks[*].text`. Signature: `score(fixture, answer_result, context)`.

Algorithm (v1 — `TextFaithfulnessScorer`):
1. Build `source_corpus`: the union of all `ContextBlock.text` values, lower-cased.
2. Tokenize `AnswerResult.answer` into candidate claim spans: numbers
   (`\d+[\.,]?\d*\s*\w+`), capitalised sequences (≥2 consecutive title-cased words),
   quoted strings.
3. For each span, check if it (or a normalised form) appears in `source_corpus`.
4. Unsupported spans → `unsupported_claims`; score = `1 - len(unsupported)/len(spans)`.
5. If `ordered_blocks` is empty or `no_answer=True`: return `score=None`, set
   `not_applicable=True`.

**Algorithm selection**: A future "semantic" implementation would be a separate class
implementing `IFaithfulnessScorer` and registered in `AnswerQualityRegistry` in its
place. There is no per-fixture mode flag — algorithm selection is a registry-level
decision, not a fixture-level one. `GoldenTestFixture` does not carry a `match_mode`
field.

**Alternatives considered**:
- Use `Context.citation_map` values: rejected — Citations carry no text, only
  metadata; cannot perform text-match faithfulness.
- Use `EvidencePack` text: rejected — EvidencePack is not a declared input for the
  faithfulness scorer; the context blocks already hold the text the LLM used.
- Per-fixture `match_mode` field: rejected — algorithm selection belongs in the
  registry, not the fixture; a fixture-level flag would create a dead field in v1
  (only `"exact"` would be supported) and couple fixture authors to scorer internals.

---

## R-04: Completeness Scoring — Facet Matching Strategy

**Question**: How should `ICompletenessScorer` match expected answer facets against
the generated answer? Is there an existing text-similarity utility to reuse?

**Finding**: `src/core/evidence_orchestrator/text_similarity.py` exists (used for
deduplication). The project also has `utils/rerank/` (cross-encoder reranker).
However, for v1 completeness scoring, the intent is to avoid live LLM/model calls.

**Decision**: v1 uses keyword-set matching:
1. Each `expected_answer_facet` string is tokenised into a set of meaningful tokens
   (stop-words stripped).
2. The `AnswerResult.answer` is tokenised the same way.
3. A facet is "covered" if ≥50% of its tokens appear in the answer token set.
4. `completeness_score = covered_facets / total_facets`.
5. If `total_facets == 0` (single-part question): `score=None`, `not_applicable=True`.

The 50% overlap threshold is configurable via `AnswerQualityConfig.completeness_overlap_threshold`.
A semantic embedding-based implementation is a valid future replacement behind the
same `ICompletenessScorer` interface.

**Algorithm selection**: Same principle as R-03 — swapping to a semantic scorer is a
registry-level decision. `GoldenTestFixture` does not carry a `match_mode` field;
algorithm mode is not a per-fixture concern.

**Alternatives considered**:
- Exact substring match: rejected — too strict; synonyms and paraphrasing would cause
  false negatives on valid answers.
- Cross-encoder reranker: rejected — requires loading a model; violates the "no live
  model calls in core scoring logic" constraint from spec 014 Assumptions.
- `text_similarity.py` character n-gram: rejected — designed for deduplication, not
  semantic facet coverage.
- Per-fixture `match_mode` field: rejected — same rationale as R-03; dead field in
  v1, couples fixture authors to scorer internals.

---

## R-05: Regression Store — Persistence Strategy

**Question**: Where and how should `EvaluationResult` records be persisted for
regression tracking?

**Finding**: No existing persistence layer in `src/core/` is suitable for
evaluation-specific records — SQLAlchemy models are project-data records (chunks,
documents, projects); adding evaluation tables would couple the quality layer to the
application DB. Celery/Redis are for task queues, not structured test result stores.

**Decision**: v1 uses a `JsonRegressionStore` that persists `EvaluationResult`
records as newline-delimited JSON in a configurable directory (default:
`.answer_quality/runs/`). Each run produces one `{run_id}.json` file. The store
exposes:
- `save(result: EvaluationResult) → Path`
- `load(run_id: str) → EvaluationResult`
- `list_runs() → list[str]`
- `diff(run_id_a: str, run_id_b: str) → RegressionDiff`

The store directory is configurable via `AnswerQualityConfig.run_store_dir`. A
database-backed store is a valid future implementation behind the same
`IRegressionStore` interface.

**Alternatives considered**:
- SQLAlchemy table: rejected — couples quality evaluation to the application DB; adds
  Alembic migration; unnecessary for offline/CI use.
- SQLite file: considered; rejected for v1 — adds SQLAlchemy dependency; JSON is
  sufficient for commit-keyed run records and more debuggable.

---

## R-06: Module Location and Naming Convention

**Question**: Where in the source tree should `answer_quality` live, and what
sub-module structure matches existing conventions?

**Finding**: All pipeline-stage modules live under `src/core/`:
`answer_generation/`, `context_builder/`, `evidence_orchestrator/`, etc. Each follows:

```
{feature}/
├── __init__.py
├── config.py       # Pydantic config model + YAML loader
├── errors.py       # domain exceptions
├── interfaces.py   # ABC interfaces
├── models.py       # domain data models
├── pipeline.py     # orchestration (runner)
├── registry.py     # factory / DI registration
└── {sub}/          # one sub-dir per pluggable concern
    ├── __init__.py
    └── {impl}.py
```

Existing test precedent for golden/fixture-driven tests:
`tests/integration/test_retrieval_planner_golden.py` — runs the full planner against
YAML fixtures in `tests/fixtures/`.

**Decision**:
- Source: `src/core/answer_quality/` (matches established convention)
- Fixtures: `tests/fixtures/answer_quality/` (matches existing fixture location)
- Unit tests: `tests/unit/core/answer_quality/`
- Integration test: `tests/integration/test_answer_quality_golden.py`

---

## R-07: Golden Fixture Format

**Question**: YAML or JSON for golden fixture files, and what fields are required?

**Finding**: Existing fixtures (`tests/fixtures/chunking/`, `tests/fixtures/document_intelligence/`)
are YAML. The retrieval planner golden test reads YAML fixtures. YAML is preferred for
human-authored test data (comments, multi-line strings, readable lists).

**Decision**: YAML format, one file per fixture set (domain or feature). Schema:

```yaml
version: "1.0.0"
fixtures:
  - question_id: "q001"
    question: "What is the standard adult dose of aspirin?"
    expected_source_ids:           # matched against EvidenceItem.doc_id (optional)
      - "doc-aspirin-pil"
    expected_answer_facets:        # for completeness scoring (optional)
      - "325 mg"
      - "every 4 to 6 hours"
    thresholds:                    # per-question overrides (optional)
      coverage: 0.8
      faithfulness: 0.8
      completeness: 0.7
```

Fields `expected_source_ids`, `expected_answer_facets`, and `thresholds` are all
optional. When absent, the corresponding scoring dimension returns N/A.

No `match_mode` field. Algorithm selection (text-matching vs semantic) is a registry
configuration, not a per-fixture property — see R-03 and R-04.

---

## Resolution Summary

| ID | Decision |
|----|----------|
| R-01 | Coverage matches `GoldenTestFixture.expected_source_ids` against `EvidenceItem.doc_id` |
| R-02 | `AnswerResult.plan_id` confirmed present; `GoldenTestResult.plan_id` correct |
| R-03 | Faithfulness corpus = `Context.ordered_blocks[*].text`; Citations carry no text |
| R-04 | Completeness = keyword-set overlap at configurable threshold (default 50%) |
| R-05 | v1 regression store = JSON files in configurable dir; `IRegressionStore` interface for future extension |
| R-06 | Module at `src/core/answer_quality/`; tests under `tests/unit/core/answer_quality/` and `tests/integration/` |
| R-07 | YAML golden fixtures in `tests/fixtures/answer_quality/`; all fields except `question_id` and `question` are optional; no `match_mode` field — algorithm mode is a registry decision (see R-03, R-04) |

# Contract: AnswerResult

**Feature**: Answer Generation (spec 013)
**Schema version**: `1.0.0`
**Status**: Stable — consumed by API layer (spec 014 Answer Quality)

## Purpose

`AnswerResult` is the public output contract of the Answer Generation pipeline. It
encapsulates the generated answer, resolved citations, conflict-disclosure flag,
no-answer flag, and grounding flags. Every downstream consumer (API layer, quality
evaluation) interacts with this schema exclusively.

## Schema

```python
class AnswerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    answer: str                              # non-empty; no-answer message when no_answer=True
    citations: list[CitationReference]       # resolved; empty when no_answer=True
    confidence_note: str | None             # optional LLM-generated limitation note
    conflicts_disclosed: bool               # True iff conflict section was injected AND answer contains disclosure
    no_answer: bool                         # True iff context was empty; LLM was NOT called
    grounding_flags: list[GroundingFlag]    # empty when grounding_check_enabled=False or all claims grounded
    plan_id: str                            # threaded from Context.plan_id
    context_id: str                         # threaded from Context.context_id
    schema_version: str = "1.0.0"
```

### `CitationReference`

```python
class CitationReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    citation_id: str          # item_id key, e.g. "ei_4a7b3c9d1e2f5678"
    document_id: str
    chunk_id: str
    document_title: str | None
    section_title: str | None
    page_number: int | None
    retrieval_score: float    # ge=0.0
```

### `GroundingFlag`

```python
class GroundingFlag(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str    # entity string absent from context
    claim: str     # text span containing the entity
    reason: str    # short code, e.g. "entity_not_in_context"
```

## Invariants

1. `answer` is never empty — on no-answer it equals `AnswerGenerationConfig.no_answer_message`.
2. `citations` is empty if and only if `no_answer=True` **or** the LLM emitted no resolvable citation markers.
3. `conflicts_disclosed` is `False` when `Context.conflicts` is empty.
4. `schema_version` major digit is always `"1"`.

## Versioning Policy

- **PATCH** (1.0.x): new optional fields, clarifications.
- **MINOR** (1.x.0): new required fields with defaults; backward-compatible.
- **MAJOR** (x.0.0): breaking shape change; requires consumer migration and `context_schema_version` bump in `AnswerGenerationConfig`.

## JSON Example

```json
{
  "answer": "The recommended adult dose is 500 mg twice daily [ei_4a7b3c9d].",
  "citations": [
    {
      "citation_id": "ei_4a7b3c9d1e2f5678",
      "document_id": "doc_pharm_001",
      "chunk_id": "chunk_042",
      "document_title": "BNF 2025",
      "section_title": "4.7.1 Non-opioid analgesics",
      "page_number": 312,
      "retrieval_score": 0.91
    }
  ],
  "confidence_note": "Based on a single source; verify against current formulary.",
  "conflicts_disclosed": false,
  "no_answer": false,
  "grounding_flags": [],
  "plan_id": "plan_abc123",
  "context_id": "ctx_def456",
  "schema_version": "1.0.0"
}
```

# Contract: ICitationFormatter

**Feature**: Answer Generation (spec 013)
**Module**: `core.answer_generation.interfaces`

## Purpose

`ICitationFormatter` scans the raw answer text for `item_id` citation markers and
resolves each one against `Context.citation_map`, producing the final
`list[CitationReference]` attached to `AnswerResult`. Markers that do not resolve are
omitted from the citation list and logged as grounding flags (handled by the pipeline,
not this interface).

## Interface

```python
class ICitationFormatter(ABC):
    @abstractmethod
    def format(
        self,
        answer_text: str,
        citation_map: dict[str, Citation],
    ) -> list[CitationReference]: ...
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `answer_text` | `str` | Answer text containing `[item_id]` markers |
| `citation_map` | `dict[str, Citation]` | From `Context.citation_map`; keys are `item_id` strings |

## Behaviour Contract

- MUST scan `answer_text` for all tokens matching the pattern `\[ei_[0-9a-f]{16}\]`
  (the canonical `item_id` prefix and 16-hex-char suffix).
- For each matched `item_id`:
  - If `item_id` is in `citation_map` → create a `CitationReference` from the
    corresponding `Citation` object.
  - If `item_id` is NOT in `citation_map` → **omit** the entry; the pipeline logs a
    grounding flag for it.
- MUST deduplicate: if the same `item_id` appears multiple times in the answer, only
  one `CitationReference` is produced.
- MUST preserve **first-appearance order** of markers (left-to-right scan).
- MUST NOT modify `answer_text` (no marker replacement — marker stripping, if desired
  by the API layer, is a presentation concern, not this stage's job).
- The method is **synchronous** (pure dict lookup and list construction).

## Key Design Decisions

- **Lookup key**: `item_id` (prefixed `ei_`) — confirmed by R-02 (research.md). Direct
  `dict` lookup, O(1) per marker.
- **Unresolved markers**: silently omitted by this interface; the pipeline catches them
  by comparing the set of markers found to the set of resolved citations and emitting
  `GroundingFlag(reason="unresolved_citation")` for each gap.

## Default Implementation

`ItemIdCitationFormatter` in `core.answer_generation.citation.item_id_formatter`.

## Example

```python
answer_text = "Adults should take 500 mg [ei_4a7b3c9d1e2f5678] twice daily."
citation_map = {
    "ei_4a7b3c9d1e2f5678": Citation(
        document_id="doc_001",
        chunk_id="chunk_042",
        retrieval_score=0.91,
        score_source="hybrid_rrf",
        section_title="4.7.1 Non-opioid analgesics",
        document_title="BNF 2025",
    )
}

result = formatter.format(answer_text, citation_map)
# → [CitationReference(citation_id="ei_4a7b3c9d1e2f5678", document_id="doc_001", ...)]
```

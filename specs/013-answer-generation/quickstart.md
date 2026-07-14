# Quickstart Validation Guide: Answer Generation (spec 013)

**Date**: 2026-07-14

This guide describes how to validate the Answer Generation pipeline end-to-end once
implementation is complete. It is a **run guide**, not an implementation guide.
Implementation code lives in `src/core/answer_generation/`; test suite in
`tests/unit/core/answer_generation/` and `tests/integration/`.

---

## Prerequisites

- Python 3.13 environment with project dependencies installed (`pip install -e ".[dev]"`
  or equivalent)
- An LLM provider configured in environment variables (or a mock; see Scenario 2)
- `specs/013-answer-generation/` artifacts present (this directory)
- Spec 012 Context Builder tests passing (upstream dependency)

---

## Scenario 1 — Happy Path: Cited Answer

**Goal**: Validate SC-001 — every cited claim maps to a valid citation.

**Setup**:

1. Build a `Context` fixture with two `ContextBlock`s and a matching `citation_map`:

```python
from core.context_builder.models import Context, ContextBlock, ContextMetadata, ConflictGroup
from core.evidence_orchestrator.models import Citation

block_a = ContextBlock(
    item_id="ei_aaaa000000000001",
    document_id="doc_001",
    text="Adults: 500 mg twice daily. [BNF 4.7.1]",
    token_count=12,
)
block_b = ContextBlock(
    item_id="ei_bbbb000000000002",
    document_id="doc_002",
    text="Avoid in renal impairment (eGFR < 30).",
    token_count=9,
)
citation_map = {
    "ei_aaaa000000000001": Citation(
        document_id="doc_001", chunk_id="chunk_01",
        retrieval_score=0.95, score_source="hybrid_rrf",
        section_title="4.7.1", document_title="BNF 2025",
    ),
    "ei_bbbb000000000002": Citation(
        document_id="doc_002", chunk_id="chunk_07",
        retrieval_score=0.88, score_source="hybrid_rrf",
    ),
}
context = Context(
    context_id="ctx_test0000000001",
    pack_id="ep_test0000000001",
    plan_id="plan_test001",
    ordered_blocks=[block_a, block_b],
    citation_map=citation_map,
    token_count=21,
    conflicts=[],
    metadata=ContextMetadata(
        items_included=2, items_dropped=0, items_compressed=0,
        budget_total=4000, budget_used=21,
    ),
    created_at="2026-07-14T00:00:00Z",
)
```

**Run**:

```python
import asyncio
from core.answer_generation.pipeline import AnswerGenerationPipeline
from core.answer_generation.config import resolve_answer_generation_config
from core.answer_generation.composition.default_composer import DefaultPromptComposer
from core.answer_generation.parsing.json_output_parser import JsonOutputParser
from core.answer_generation.citation.item_id_formatter import ItemIdCitationFormatter
from core.answer_generation.grounding.entity_tag_checker import EntityTagGroundingChecker
from stores.llm.LLMProviderFactory import LLMProviderFactory

llm = LLMProviderFactory(config={"llm_provider": "openai", ...}).create("openai")
config = resolve_answer_generation_config("generic")

pipeline = AnswerGenerationPipeline(
    composer=DefaultPromptComposer(),
    parser=JsonOutputParser(),
    citation_formatter=ItemIdCitationFormatter(),
    grounding_checker=EntityTagGroundingChecker(),
    llm=llm,
)

result = asyncio.run(pipeline.run(context=context, question="What is the adult dose?", config=config))
```

**Expected outcome**:

- `result.no_answer == False`
- `result.citations` is non-empty
- Every `citation.citation_id` in `result.citations` is a key in `citation_map`
- `result.conflicts_disclosed == False`
- `result.grounding_flags` is empty (assuming LLM only cites provided blocks)

---

## Scenario 2 — Unit Test with LLM Mock

**Goal**: Validate the pipeline without a real LLM provider.

**Run**:

```bash
pytest tests/unit/core/answer_generation/ -v
```

The unit tests use a mock `LLMInterface` that returns a deterministic JSON string
(see `tests/unit/core/answer_generation/conftest.py`).

**Expected**: All unit tests pass with zero LLM calls to external APIs.

---

## Scenario 3 — Conflict Disclosure

**Goal**: Validate SC-002 — conflicts in `Context` produce explicit disclosure.

**Setup**: Same as Scenario 1, but add a `ConflictGroup` to the `context`:

```python
from core.context_builder.models import ConflictGroup

conflict = ConflictGroup(
    entity_tag="paracetamol",
    attribute="max_daily_dose",
    item_ids=["ei_aaaa000000000001", "ei_bbbb000000000002"],
    resolution=None,
)
# Rebuild context with conflicts=[conflict]
```

**Expected outcome**:

- `result.conflicts_disclosed == True`
- `result.answer` contains language such as "Sources differ" or "conflicting information"
  (the exact wording depends on the LLM; the disclosure header from config is present in
  the prompt)

---

## Scenario 4 — No-Answer on Empty Context

**Goal**: Validate SC-003 — empty context returns explicit no-answer, no LLM call.

**Setup**: Build a `Context` with `ordered_blocks=[]` and `citation_map={}`:

```python
empty_context = Context(
    context_id="ctx_empty000000001",
    pack_id="ep_empty000000001",
    plan_id="plan_test002",
    ordered_blocks=[],
    citation_map={},
    token_count=0,
    conflicts=[],
    metadata=ContextMetadata(
        items_included=0, items_dropped=5, items_compressed=0,
        budget_total=4000, budget_used=0,
    ),
    created_at="2026-07-14T00:00:00Z",
)
```

**Expected outcome**:

- `result.no_answer == True`
- `result.answer == config.no_answer_message`
- `result.citations == []`
- Mock LLM's `generate_text_async` is **never called** (assert call count = 0)

---

## Scenario 5 — Provider Swap (SC-004)

**Goal**: Validate that swapping the LLM provider requires zero pipeline changes.

**Run**:

```python
# Swap from OpenAI to Azure OpenAI — only config changes
llm_azure = LLMProviderFactory(config={"llm_provider": "azure_openai", ...}).create("azure_openai")

pipeline_azure = AnswerGenerationPipeline(
    composer=DefaultPromptComposer(),
    parser=JsonOutputParser(),
    citation_formatter=ItemIdCitationFormatter(),
    grounding_checker=EntityTagGroundingChecker(),
    llm=llm_azure,  # ← only change
)
result = asyncio.run(pipeline_azure.run(context=context, question="What is the adult dose?", config=config))
```

**Expected**: `result` has the same shape as Scenario 1; pipeline code is unchanged.

---

## Scenario 6 — Grounding Flag

**Goal**: Validate SC-006 / FR-007 — ungrounded entity in answer is flagged, not blocked.

**Setup**: Use a mock LLM that returns an answer mentioning an entity not in the context
blocks (e.g. "Metformin XR" when the context only contains "Metformin").

**Expected outcome**:

- `result.grounding_flags` contains at least one `GroundingFlag` with
  `entity="Metformin XR"` and `reason="entity_not_in_context"`
- `result.answer` is still returned (not empty)

---

## Integration Test

```bash
pytest tests/integration/test_answer_generation_e2e.py -v
```

Covers: valid `Context` → `AnswerResult` round-trip with a mock LLM, verifying
citation resolution, conflict disclosure, no-answer guard, and `AnswerResult`
schema version.

---

## Contract References

- Output schema: [AnswerResult.md](contracts/AnswerResult.md)
- Interface contracts: [IPromptComposer.md](contracts/IPromptComposer.md),
  [IOutputParser.md](contracts/IOutputParser.md),
  [ICitationFormatter.md](contracts/ICitationFormatter.md),
  [IGroundingChecker.md](contracts/IGroundingChecker.md)
- Data model: [data-model.md](data-model.md)

# Feature Specification: Answer Generation

**Feature Branch**: `013-answer-generation`

**Created**: 2026-07-14

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Cited Answer from Valid Context (Priority: P1)

A downstream consumer (API layer, application client) submits a user question together
with a fully-populated `Context` object. The Answer Generation stage produces an
`AnswerResult` containing: an answer text, a citation list where every cited claim maps
to a `Context.citation_map` entry (document id, section, excerpt), and a
confidence/limitations note. The consumer can display the answer and citations to the
end user.

**Why this priority**: Core value delivery — without a structured, citable answer the
entire RAG pipeline produces no user-facing output.

**Independent Test**: Supply a pre-built `Context` fixture with a populated
`citation_map` and non-empty `ordered_blocks`. Invoke Answer Generation. Verify
`AnswerResult.citations` is non-empty and each `citation_id` resolves in the original
`Context.citation_map`.

**Acceptance Scenarios**:

1. **Given** a `Context` with `ordered_blocks` containing three chunks and a matching
   `citation_map`, **When** Answer Generation is invoked, **Then** `AnswerResult.answer`
   is non-empty and `AnswerResult.citations` contains at least one entry with a valid
   `citation_id`, `document_id`, `section`, and `excerpt`.

2. **Given** a `Context` whose `citation_map` has five entries and the LLM references
   three of them, **When** citation formatting runs, **Then** `AnswerResult.citations`
   contains exactly those three entries — no phantom citations and no missing ones.

3. **Given** a `Context` with domain module injected via field-pack config,
   **When** the prompt is composed, **Then** the assembled prompt contains the
   domain-specific instructions provided by config without any hardcoded domain content
   in the core pipeline.

---

### User Story 2 — Conflict Disclosure in Answer (Priority: P2)

A user submits a question against a `Context` where `Context.conflicts` is non-empty
(the Context Builder identified contradictory claims from different sources). The
generated answer must explicitly disclose the disagreement rather than silently
picking one side.

**Why this priority**: Factual integrity — silently resolving conflicts introduces
undetected misinformation into the answer.

**Independent Test**: Supply a `Context` fixture where `conflicts` contains one or more
conflict descriptors. Invoke Answer Generation. Inspect `AnswerResult.answer` for
explicit disclosure language and verify `AnswerResult.conflicts_disclosed` is `True`.

**Acceptance Scenarios**:

1. **Given** a `Context` where `conflicts` contains one conflict between two sources,
   **When** Answer Generation produces the answer, **Then** the answer text explicitly
   mentions the disagreement (e.g., "Sources differ on …") and
   `AnswerResult.conflicts_disclosed` is `True`.

2. **Given** a `Context` where `conflicts` is empty, **When** Answer Generation runs,
   **Then** no conflict-disclosure language is injected and
   `AnswerResult.conflicts_disclosed` is `False`.

---

### User Story 3 — Explicit No-Answer for Insufficient Context (Priority: P2)

When `Context.ordered_blocks` is empty or the token budget is zero, Answer Generation
must return an explicit "not found in provided sources" response rather than invoking
the LLM and risking a hallucinated answer.

**Why this priority**: Hallucination prevention is a non-negotiable safety property for
a production RAG system.

**Independent Test**: Supply an empty `Context` (no blocks, empty `citation_map`).
Invoke Answer Generation. Verify the pipeline returns before the LLM call and
`AnswerResult.no_answer` is `True` with an appropriate message.

**Acceptance Scenarios**:

1. **Given** a `Context` with no `ordered_blocks` and an empty `citation_map`,
   **When** Answer Generation is invoked, **Then** `AnswerResult.no_answer` is `True`,
   `AnswerResult.answer` is a human-readable "not found in provided sources" message,
   and no LLM call is made.

2. **Given** a `Context` that has blocks but all carry zero token weight,
   **When** Answer Generation is invoked, **Then** the response still applies the
   no-answer path rather than composing an empty prompt.

---

### User Story 4 — Grounding Flag for Out-of-Context Claims (Priority: P3)

After the LLM generates an answer, the Grounding Checker inspects whether the answer
references entities or claims absent from `Context`. Flagged answers are annotated in
`AnswerResult` for downstream logging and evaluation. The pipeline does **not** block
or retry on a grounding flag.

**Why this priority**: Enables offline quality evaluation and drift detection without
adding latency or blocking the answer path.

**Independent Test**: Supply a `Context` with a narrow `entity_tags` set and mock an
LLM response that introduces an entity not present in the context. Verify
`AnswerResult.grounding_flags` is non-empty and the answer is still returned.

**Acceptance Scenarios**:

1. **Given** an LLM response mentioning entity "X" that does not appear in any
   `EvidenceItem.entity_tags` within the `Context`, **When** the Grounding Checker
   runs, **Then** `AnswerResult.grounding_flags` contains an entry identifying entity
   "X" as ungrounded, and `AnswerResult.answer` is still returned to the caller.

2. **Given** an LLM response whose every claim maps back to a context entity,
   **When** the Grounding Checker runs, **Then** `AnswerResult.grounding_flags` is
   empty.

---

### Edge Cases

- What happens when the LLM provider raises an exception mid-generation?
  — The pipeline propagates a structured `AnswerGenerationError` with provider context;
  partial results are not returned.
- What happens when `Context.citation_map` is populated but the LLM response contains
  no citation markers?
  — `AnswerResult.citations` is empty; `AnswerResult.answer` is still returned
  (uncited answer is valid, grounding check may flag it).
- What happens when a `citation_id` in the LLM response does not exist in
  `Context.citation_map`?
  — The unknown citation is omitted from `AnswerResult.citations` and logged as a
  grounding flag.
- What happens when the configured domain module in the field-pack references a
  non-existent capability?
  — Pipeline raises `AnswerGenerationError` at prompt composition, before the LLM call.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST accept a `Context` object (schema v1.0.0 per spec 012)
  as its sole structured input alongside the user question string.
- **FR-002**: `IPromptComposer` MUST assemble the final prompt from
  `Context.ordered_blocks`, the user question, system instructions, and zero or more
  domain capability modules injected via field-pack config — no domain content
  hardcoded in the core.
- **FR-003**: When `Context.conflicts` is non-empty, the pipeline MUST inject
  conflict-disclosure instructions into the prompt so the LLM explicitly discloses
  disagreements; silent conflict resolution is prohibited.
- **FR-004**: The pipeline MUST enforce a structured output contract — `AnswerResult`
  (answer text, citation list, confidence/limitations note, conflict-disclosure flag,
  no-answer flag, grounding flags) — via schema-constrained generation or
  post-generation parse validation.
- **FR-005**: The LLM call MUST be delegated to the existing `LLMProviderFactory`; no
  new provider abstraction may be introduced by this feature.
- **FR-006**: `ICitationFormatter` MUST map citation markers in the generated answer to
  `Context.citation_map` entries (document id, section, excerpt), producing
  `AnswerResult.citations`; unresolved markers are omitted and logged.
- **FR-007**: `IGroundingChecker` MUST flag (not block) claims in the generated answer
  that reference entities absent from `Context`; flags are recorded in
  `AnswerResult.grounding_flags` and the answer is still returned.
- **FR-008**: When `Context.ordered_blocks` is empty, the pipeline MUST return an
  explicit no-answer `AnswerResult` (human-readable "not found in provided sources"
  message, `no_answer=True`) without invoking the LLM.
- **FR-009**: Domain-specific prompt behaviour MUST be injected exclusively through
  `answer_generation.yaml`-style field-pack config; the core pipeline MUST remain
  domain-agnostic.
- **FR-010**: The pipeline MUST validate `Context.schema_version` major version at
  entry; a version mismatch MUST raise `AnswerGenerationError` before any processing.
  ⚠ **Cross-spec dependency**: spec 012's `Context` Key Entities definition does not
  currently include a `schema_version` field. FR-010 cannot be implemented until spec
  012 adds `schema_version: "1.0.0"` to the `Context` schema. This MUST be resolved
  as a pre-condition before `/speckit-plan` for this feature (see Assumptions).

### Key Entities

- **AnswerResult**: Final output contract — `answer` (str), `citations` (list of
  resolved citation references), `confidence_note` (str | None),
  `conflicts_disclosed` (bool), `no_answer` (bool), `grounding_flags` (list of
  ungrounded entity/claim descriptors), `schema_version` ("1.0.0").
- **CitationReference**: Individual resolved citation — `citation_id` (str),
  `document_id` (str), `section` (str | None), `excerpt` (str | None), `score`
  (float | None).
- **GroundingFlag**: Descriptor for an ungrounded claim — `claim` (str), `entity`
  (str | None), `reason` (str).
- **IPromptComposer**: Interface — `compose(context: Context, question: str, modules: list[CapabilityModule]) -> ComposedPrompt`.
- **IOutputParser**: Interface — `parse(raw: str | dict) -> AnswerResult`.
- **ICitationFormatter**: Interface — `format(answer: AnswerResult, citation_map: dict) -> AnswerResult`.
- **IGroundingChecker**: Interface — `check(answer: AnswerResult, context: Context) -> list[GroundingFlag]`.
- **CapabilityModule**: Config-injected domain instruction block — `name` (str),
  `instructions` (str), `priority` (int).

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries — interfaces in
  domain/application, implementations in infrastructure, composition in the pipeline
  entry point.
- **NFR-002**: All pipeline stages MUST be async; public APIs MUST include full type
  hints.
- **NFR-003**: LLM provider MUST be swappable via `LLMProviderFactory` with no changes
  to core pipeline logic.
- **NFR-004**: `AnswerResult.citations` MUST be present in every non-empty LLM
  response; answers lacking citations are flagged but not blocked.
- **NFR-005**: Prompt templates and system instructions injected by domain modules MUST
  be versioned when modified.
- **NFR-006**: Unit tests MUST cover each pipeline stage independently (composer,
  conflict injector, output parser, citation formatter, grounding checker, no-answer
  path); integration tests MUST cover the end-to-end pipeline with a real LLM mock.
- **NFR-007**: Structured logging MUST record `request_id`, `plan_id` (threaded from
  `Context`), LLM provider name, token usage, and grounding flag count at the pipeline
  boundary.
- **NFR-008**: No API keys or credentials may appear in source control; provider
  selection is config-driven.
- **NFR-009**: Prometheus metrics MUST be extended to capture answer generation
  latency, citation resolution rate, no-answer rate, and grounding flag rate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a `Context` with a valid `citation_map`, every cited claim in the
  produced `AnswerResult` maps to a valid citation — zero phantom or dangling
  citation references.
- **SC-002**: When `Context.conflicts` is non-empty, the produced answer explicitly
  discloses the disagreement in 100% of cases — zero silent conflict resolutions.
- **SC-003**: When `Context.ordered_blocks` is empty, Answer Generation returns an
  explicit no-answer response in 100% of cases — zero hallucinated answers on empty
  context.
- **SC-004**: Swapping the LLM provider (e.g., OpenAI → Azure OpenAI) requires zero
  changes to pipeline code — only config changes.
- **SC-005**: The answer generation stage (prompt composition through citation
  formatting, excluding LLM call latency) completes in under 200 ms for a
  representative `Context` of 4 000 tokens on standard hardware.
- **SC-006**: The grounding checker introduces no measurable latency increase on the
  answer path (flag-only, no blocking retry or LLM re-call).
- **SC-007**: Validated against the golden query set from spec 014 (Answer Quality):
  citation correctness ≥ 95%, conflict disclosure rate = 100%, no-answer precision
  ≥ 99%.

## Assumptions

- `Context` schema v1.0.0 (spec 012) is stable and will not change between planning
  and implementation of this feature.
- **[Confirmed — R-01]** `Context.schema_version: str = "1.0.0"` is already present
  in `src/core/context_builder/models.py`. The cross-spec dependency note raised during
  specification was against the spec 012 *document*; the code contract is correct.
  FR-010 is implementable with no changes to spec 012.
- **[Confirmed — R-09]** `Context.context_id` and `Context.plan_id` are first-class
  fields on the frozen `Context` model (confirmed via direct code inspection of
  `src/core/context_builder/models.py`). `AnswerGenerationPipeline` reads them directly
  and copies them into `AnswerResult`; no additional pipeline parameters are needed.
- `Context.citation_map` keys are `item_id` values drawn from `EvidenceItem.item_id`
  (spec 011) / `ContextBlock.item_id` (spec 012). Citation markers the LLM emits in
  raw answer text are expected to reference these same `item_id` values.
  `ICitationFormatter` MUST use `item_id` as the unambiguous lookup key when resolving
  markers to `citation_map` entries; no secondary key or alias resolution is required.
- `LLMProviderFactory` (existing infrastructure) supports structured/JSON-mode output
  or the pipeline can post-parse plain-text LLM responses against the output schema.
- Field-pack config files (`answer_generation.yaml`) follow the same resolution
  hierarchy as established in spec 002 (Field Registry): generic < domain < project.
- Deep faithfulness scoring, hallucination benchmarking, and regression tracking are
  explicitly out of scope — those belong to spec 014 (Answer Quality).
- No retrieval, evidence orchestration, or context building occurs within this feature;
  all upstream pipeline work is already complete when Answer Generation is invoked.
- Domain modules are stateless instruction blocks; they do not require their own
  infrastructure or external calls.
- `Context.plan_id` (threaded from spec 009, Retrieval Planner) is available for
  structured log correlation and does not require further transformation.
- The `IGroundingChecker` implementation in this spec is lightweight (entity/claim
  lookup against context); deep semantic faithfulness scoring is deferred to spec 014.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/013-answer-generation/plan.md`

Related:
- `specs/013-answer-generation/` — **active**; Answer Generation: seven-stage async pipeline (version gate → no-answer guard → prompt composition → conflict-disclosure injection → LLM call → output parsing → citation formatting → grounding check) consuming `Context` (spec 012) and emitting `AnswerResult` (schema v1.0.0); four pluggable interfaces (`IPromptComposer`, `IOutputParser`, `ICitationFormatter`, `IGroundingChecker`); `AnswerResult` is the stable public contract for spec 014 (Answer Quality); domain behaviour injected via `answer_generation.yaml` field-pack config (generic < domain < project); LLM call delegates to existing `LLMProviderFactory`.
- `specs/012-context-builder/` — **dependency (active)**; `Context` (schema v1.0.0) is the primary input; `Context.citation_map` keys are `item_id` values (`ei_` prefix) — the unambiguous lookup key for `ICitationFormatter`; `Context.conflicts` drives conflict-disclosure injection; `Context.schema_version` major-version checked at pipeline entry (FR-010); `Context.plan_id` threaded into `AnswerResult` for correlation.
- `specs/011-evidence-orchestrator/` — **dependency (active)**; `Citation` model (from `core.evidence_orchestrator.models`) is the value type in `Context.citation_map`; `EvidenceItem.entity_tags` are the entity vocabulary for the grounding checker.
- `specs/009-retrieval-planner/` — **dependency (complete)**; `plan_id` threaded through `EvidencePack` → `Context` → `AnswerResult`.
- `specs/002-field-registry/` — dependency; field packs supply answer generation configuration via `answer_generation.yaml`; controls `system_prompt_template`, `capability_modules`, temperature, output tokens, grounding check toggle.
- `specs/005-answer-quality/` — **downstream**; `AnswerResult` is the input contract; golden query set used for SC-007 acceptance criteria.
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

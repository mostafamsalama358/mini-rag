<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/014-answer-quality/plan.md`

Related:
- `specs/014-answer-quality/` — **active**; Answer Quality: offline evaluation and gating layer measuring the full AlgoRAG pipeline (006–013); five interfaces (`IGoldenTestRunner`, `ICoverageEvaluator`, `IFaithfulnessScorer`, `ICompletenessScorer`, `IRegressionStore`); consumes `AnswerResult` (013), `Context` (012), `EvidencePack` (011) as read-only inputs; golden fixtures in YAML; `EvaluationResult` (schema v1.0.0) is the stable CI-consumable output; module at `src/core/answer_quality/`; coverage matches on `EvidenceItem.doc_id`; faithfulness corpus built from `Context.ordered_blocks[*].text`.
- `specs/013-answer-generation/` — **dependency (complete)**; `AnswerResult` (schema v1.0.0) is the primary scored artifact; `AnswerResult.plan_id` and `.context_id` threaded into `GoldenTestResult` for correlation; `IGroundingChecker` is the lightweight inline guard (distinct from `IFaithfulnessScorer` which is the deeper offline scorer).
- `specs/012-context-builder/` — **dependency (complete)**; `Context` (schema v1.0.0) supplies `ordered_blocks[*].text` for faithfulness corpus; `citation_map` keys are `item_id` values (`ei_` prefix); `Context.plan_id` threaded into `GoldenTestResult`.
- `specs/011-evidence-orchestrator/` — **dependency (complete)**; `EvidencePack.items[*].doc_id` is the coverage matching key; `EvidencePack` is the pre-trimming retrieval boundary, capturing sources dropped before context budget.
- `specs/009-retrieval-planner/` — **dependency (complete)**; `plan_id` threaded through `EvidencePack` → `Context` → `AnswerResult` → `GoldenTestResult`.
- `specs/002-field-registry/` — dependency; `AnswerQualityConfig` follows the same field-pack pattern (`src/fields/generic/answer_quality.yaml`; domain packs override thresholds).
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

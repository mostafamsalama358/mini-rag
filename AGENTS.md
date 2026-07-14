<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/012-context-builder/plan.md`

Related:
- `specs/012-context-builder/` — **active**; Context Builder: eight-stage async pipeline (allocate budget → select under budget → compress → detect conflicts → stitch → final dedup → assemble) consuming `EvidencePack` (spec 011) and emitting a token-budget-compliant `Context`; four pluggable interfaces (`ITokenBudgetAllocator`, `IContextCompressor`, `IConflictDetector`, `IContextStitcher`); `Context` is the stable public contract for spec 013 (Answer Generation); schema versioned at `1.0.0`; domain behaviour injected via `context_builder.yaml` field-pack config (generic < domain < project).
- `specs/011-evidence-orchestrator/` — **dependency (active)**; `EvidencePack` (schema v1.0.0) is the primary input; `EvidenceItem` carries `entity_tags`, `section_path`, `compressibility_score`, `citation`, `relevance_score`; `ITokenCounter`, `char_ngrams`, `jaccard_similarity` reused directly (no duplication); `EvidencePack.schema_version` major-version checked at pipeline entry.
- `specs/009-retrieval-planner/` — **dependency (complete)**; `plan_id` threaded through `EvidencePack` into `Context`.
- `specs/008-knowledge-representation/` — **dependency (complete)**; `entity_tags` on `EvidenceItem` carry KnowledgeUnit canonical forms used by `IConflictDetector` for entity grouping.
- `specs/002-field-registry/` — dependency; field packs supply context builder configuration via `context_builder.yaml`; controls budget reservations, compressibility threshold, dedup threshold, compression strategy.
- `specs/001-pharmacy-query-enhancement/` — **superseded**; pharmacy work is Phase D in `002-field-registry/spec.md`
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

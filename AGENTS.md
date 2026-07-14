<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/009-retrieval-planner/plan.md`

Related:
- `specs/009-retrieval-planner/` — **active**; Retrieval Planner: stateless, deterministic pipeline converting `ParseResult` (spec 004) into immutable `RetrievalPlan`; six pluggable stages (IIntentClassifier → IEntityResolver → IFilterExtractor → IClarificationDetector → IStrategySelector → BudgetEstimator → PlanAssembler); `RetrievalPlan` is the stable public contract for specs 010–013; open `StrategyType`, `RetrievalLimits` with `max_candidates`, `RetrievalConstraints`, advisory `ExecutionHints`; zero retrieval ops in core; schema versioned at `1.0.0`.
- `specs/008-knowledge-representation/` — **dependency (complete)**; `KnowledgePackage` produced upstream; entity metadata available as reference for entity resolution but NOT queried at plan time.
- `specs/007-intelligent-chunking-engine/` — **dependency (complete)**; `ChunkSet` produced upstream; metadata available as reference but NOT queried at plan time.
- `specs/006-document-intelligence-pipeline/` — **dependency (complete)**; Canonical Document Model (`DocumentModel`/`StructuralElement`).
- `specs/004-semantic-query-parser/` — **dependency (complete)**; `ParseResult` (carrying `QueryPlan`) is the sole input to the Retrieval Planner.
- `specs/003-architecture-refactor/` — dependency; `core/` layering hosting the planner at `src/core/retrieval_planner/`.
- `specs/002-field-registry/` — dependency; field packs supply planner configuration via `retrieval_planning.yaml` (generic < domain < project precedence); controls strategy vocabulary, budget defaults, confidence thresholds.
- `specs/001-pharmacy-query-enhancement/` — **superseded**; pharmacy work is Phase D in `002-field-registry/spec.md`
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

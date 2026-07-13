<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/006-document-intelligence-pipeline/plan.md`

Related:
- `specs/006-document-intelligence-pipeline/` — **active**; structured Document Model (section/paragraph/table/table-row/list/list-item) parsed before chunking; generic core + YAML `element_mapping` packs only; no domain-name logic in core.
- `specs/005-answer-quality/` — dependent; answer completeness & faithfulness (NotebookLM-level quality metrics AQ-1…AQ-6) — its AQ-1/AQ-2 retrieval-coverage targets depend on this feature's structure-preserving chunking.
- `specs/004-semantic-query-parser/` — dependency; QueryPlan / semantic parse feeding retrieval.
- `specs/003-architecture-refactor/` — dependency; `services/rag/` hosting answer orchestration.
- `specs/002-field-registry/` — dependency; field packs supply chunking/retrieval strategies, prompts.
- `specs/001-pharmacy-query-enhancement/` — **superseded**; pharmacy work is Phase D in `002-field-registry/spec.md`
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

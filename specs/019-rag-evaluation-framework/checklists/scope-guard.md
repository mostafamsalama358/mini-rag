# Scope Guard: RAG Evaluation Framework (019)

**Purpose**: Prevent architecture-phase drift into implementation or parallel production paths.

## MUST NOT appear in 019 architecture deliverables

- [x] Algorithms, formulas, or concrete numeric thresholds
- [x] Production evaluation runner / scorer / judge engine implementation
- [x] CI workflow YAML or CI/dashboard vendor selection
- [x] Parallel retrieval or answer production path
- [x] Request-path mandatory evaluation as answer owner
- [x] Redefinition of 014 Faithfulness/Completeness semantics
- [x] New 016 production sole owner (“Evaluation” / “Quality”) for traffic
- [x] Coupling to 017 ingest job control-plane entities
- [x] Future extension implementations (agent/multimodal/etc.) as delivery

## MUST remain true

- [x] Evaluation offline / CI / shadow / monitoring only
- [x] Contracts under `contracts/` are normative; governance summarizes
- [x] Metric Ownership has exactly one Primary Owner per metric
- [x] 019 gates win over 018 diagnostics for release decisions
)

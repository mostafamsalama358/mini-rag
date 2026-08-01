# Evaluation Architecture Review Checklist (019)

**Purpose**: Gate review for evaluation-architecture / quality-evaluation contract changes.

**References**: `contracts/metric-system.md`, `contracts/compatibility.md`, `governance/evaluation-non-ownership-freeze.md`

## MUST

- [x] Every canonical metric has exactly one Primary Owner
- [x] Profiles bind dataset tiers + gate types without inventing parallel production paths
- [x] PR / Release pins require Frozen datasets/benchmarks where applicable
- [x] Judge Layer preserves metric identity across Rule/LLM/Human/Hybrid
- [x] Error Taxonomy and Drift Taxonomy are used for reporting
- [x] Alerts notify; gates decide
- [x] Compatibility with 014–018 preserved (014 semantics; 016 sole-owner; 015 no second owner; 018 diagnostics non-authoritative vs 019 gates)

## MUST REJECT

- [x] Parallel answer/retrieval path for “evaluation mode”
- [x] Request-path evaluation as production owner
- [x] New production “Quality/Evaluation Owner” sole owner
- [x] Silent PASS when required judge/shadow/dataset freeze is unavailable
- [x] In-place mutation of Frozen Core Golden / Frozen Benchmark
- [x] Redefining Faithfulness/Completeness incompatibly with 014
- [x] Letting 018 stage heuristics override 019 release gates
- [x] Encoding concrete thresholds/formulas as architecture identity
)

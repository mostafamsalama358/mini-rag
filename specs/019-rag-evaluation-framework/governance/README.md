# Evaluation Framework Governance (019)

**Purpose**: Index evaluation-architecture registries and procedures. Normative rules live in `../contracts/`. Governance files **summarize/index** contracts — they MUST NOT invent divergent rules.

**Not**: implementation catalog, algorithms, formulas, numeric thresholds, CI vendor choice, or production pipeline code.

## How to find the evaluation owner / attribute a PR gate failure

1. Open [`metric-ownership-registry.md`](./metric-ownership-registry.md) — exactly one **Primary Owner** per failed metric.
2. Classify with [`error-taxonomy-catalog.md`](./error-taxonomy-catalog.md).
3. Optionally annotate root cause via [`metric-dependency-map.md`](./metric-dependency-map.md) — **do not** reassign Primary Owner.
4. Confirm profile/gate binding in [`evaluation-profile-index.md`](./evaluation-profile-index.md) and CI posture in [`ci-integration-summary.md`](./ci-integration-summary.md).
5. Cross-check sole-owner baseline in `specs/016-architecture-consolidation/governance/ownership-registry.md`.
6. **Never invent a new production RAG stage** for evaluation. Evaluation is offline / CI / shadow / monitoring only ([`evaluation-non-ownership-freeze.md`](./evaluation-non-ownership-freeze.md)).

## Registry index

| Artifact | Role |
|----------|------|
| [metric-ownership-registry.md](./metric-ownership-registry.md) | Canonical metrics → Primary Owner |
| [metric-dependency-map.md](./metric-dependency-map.md) | Upstream/downstream / root-cause annotation |
| [evaluation-profile-index.md](./evaluation-profile-index.md) | Smoke→Production Monitoring profiles |
| [judge-layer-registry.md](./judge-layer-registry.md) | Rule / LLM / Human / Hybrid |
| [metric-confidence-notes.md](./metric-confidence-notes.md) | Optional confidence / provenance |
| [error-taxonomy-catalog.md](./error-taxonomy-catalog.md) | Eight failure categories |
| [failure-vignette-catalog.md](./failure-vignette-catalog.md) | Attributable failure examples |
| [slice-dimension-catalog.md](./slice-dimension-catalog.md) | Standard report slices |
| [retrieval-evaluation-notes.md](./retrieval-evaluation-notes.md) | IR metric scope |
| [planner-evaluation-notes.md](./planner-evaluation-notes.md) | Planner metric scope |
| [dataset-benchmark-governance-summary.md](./dataset-benchmark-governance-summary.md) | Freeze / lineage / reproducibility |
| [experiment-role-catalog.md](./experiment-role-catalog.md) | Baseline…Canary |
| [evaluation-run-metadata-catalog.md](./evaluation-run-metadata-catalog.md) | Reproducibility fields |
| [composite-score-catalog.md](./composite-score-catalog.md) | Derived rollups (no formulas) |
| [drift-taxonomy-catalog.md](./drift-taxonomy-catalog.md) | Live drift categories |
| [alert-catalog.md](./alert-catalog.md) | Alerts notify; gates decide |
| [monitoring-view-index.md](./monitoring-view-index.md) | Dashboard information architecture |
| [evaluation-lifecycle.md](./evaluation-lifecycle.md) | Dataset→…→Dataset Evolution |
| [evaluation-entity-catalog.md](./evaluation-entity-catalog.md) | Logical entities from data-model |
| [ci-integration-summary.md](./ci-integration-summary.md) | CI contract summary |
| [relationship-to-014-018.md](./relationship-to-014-018.md) | Compatibility stance |
| [evaluation-non-ownership-freeze.md](./evaluation-non-ownership-freeze.md) | No production eval stage |
| [future-extension-points.md](./future-extension-points.md) | Non-scope placeholders |
| [quickstart-results.md](./quickstart-results.md) | Architecture validation results |

## Normative contracts (source of truth)

See `../contracts/` — especially `metric-system.md`, `evaluation-pipeline.md`, `compatibility.md`.
)

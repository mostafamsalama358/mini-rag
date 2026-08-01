# RAG Quality Architecture Governance (018)

**Purpose**: Quality contracts, continuity registries, and review artifacts for maximizing retrieval, evidence, grounding, and answer quality — **without** implementation catalogs, algorithms, provider winners, or parallel pipelines.

**Normative sources** (do not diverge):
- [`../spec.md`](../spec.md) — architecture specification §§1–20, Contracts C1–C12
- [`../contracts/`](../contracts/) — normative contract files
- [`../data-model.md`](../data-model.md) — architectural entities
- [`../plan.md`](../plan.md) / [`../research.md`](../research.md)

Governance files here **summarize and index** those sources for reviewability. If a registry conflicts with a contract file, the contract wins (see T064 note below).

---

## How to find the quality owner

1. Open [`stage-ownership-map.md`](./stage-ownership-map.md) and find the concern.
2. Confirm continuity via [`continuity-contract-index.md`](./continuity-contract-index.md) (C1–C12).
3. For defect attribution, use [`defect-attribution-guide.md`](./defect-attribution-guide.md) + [`failure-vignette-catalog.md`](./failure-vignette-catalog.md).
4. For cumulative diagnostics, use [`quality-context-trace-registry.md`](./quality-context-trace-registry.md).
5. Cross-check sole-owner baseline in `specs/016-architecture-consolidation/governance/ownership-registry.md`.
6. **Never invent a “Quality Owner.”** Extend the canonical stage owner.

Code inspection is last resort, not the source of ownership truth.

---

## Artifact index

| Artifact | Role |
|----------|------|
| [stage-ownership-map.md](./stage-ownership-map.md) | Concern → primary owner |
| [continuity-contract-index.md](./continuity-contract-index.md) | C1–C12 index |
| [quality-entity-catalog.md](./quality-entity-catalog.md) | Entity summaries |
| [failure-vignette-catalog.md](./failure-vignette-catalog.md) | Bad-answer attribution |
| [defect-attribution-guide.md](./defect-attribution-guide.md) | Engineer procedure |
| [continuity-worked-examples.md](./continuity-worked-examples.md) | Narrative continuity |
| [stage-quality-metrics.md](./stage-quality-metrics.md) | Architecture metrics (≠ 014 redefinition) |
| [stakeholder-outcomes.md](./stakeholder-outcomes.md) | SC → outcomes |
| [no-answer-decision-catalog.md](./no-answer-decision-catalog.md) | No-answer conditions |
| [grounding-and-citation-onepager.md](./grounding-and-citation-onepager.md) | Claim grounding + citation chain |
| [offline-feedback-loop.md](./offline-feedback-loop.md) | 014 feedback flow |
| [quality-context-trace-registry.md](./quality-context-trace-registry.md) | Quality Context + Trace |
| [extension-points-registry.md](./extension-points-registry.md) | Stage extensions |
| [modularity-freeze.md](./modularity-freeze.md) | C8 / M0 freeze |
| [anti-shortcut-index.md](./anti-shortcut-index.md) | Rejectable shortcuts |
| [relationship-to-014-017.md](./relationship-to-014-017.md) | Compatibility |
| [quickstart-results.md](./quickstart-results.md) | Validation results |

**Contract primacy note (T064)**: `contracts/*.md` remain normative. Registries must not invent divergent rules.

---

## Explicit non-goals

- Pipeline implementation, algorithms, formulas, thresholds, providers
- Second retrieval or answer path
- Redefining Feature 014 golden metrics
- Coupling to Feature 017 ingest job control plane

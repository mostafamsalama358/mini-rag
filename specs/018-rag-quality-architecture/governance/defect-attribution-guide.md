# Defect Attribution Guide (018)

For quality engineers mapping bad answers to the earliest broken contract.

## Procedure

1. **Capture symptoms** — missing filter, false completeness, silent conflict, broken citation, ungrounded claim, ignored ambiguity, etc.
2. **Inspect Quality Context** — ambiguity, sufficiency, conflict summary, citation completeness, budget usage, grounding status, degradation history ([`quality-context-trace-registry.md`](./quality-context-trace-registry.md)).
3. **Inspect Quality Trace sections** in order Plan → Retrieval → Expansion → Fusion → Rerank → Evidence → Context → Generation → Verification.
4. **Find earliest break** — use [`continuity-contract-index.md`](./continuity-contract-index.md) (C1–C12).
5. **Confirm owner** — [`stage-ownership-map.md`](./stage-ownership-map.md); remediate that stage’s contract — do not “fix” a downstream stage to hide upstream dishonesty.
6. **Compare vignettes** — [`failure-vignette-catalog.md`](./failure-vignette-catalog.md).

## Heuristics

| If you see… | Look first at |
|-------------|----------------|
| Wrong entity/filter scope | C2 then C9 |
| Plan vs parse intent mismatch | C9 |
| Unplanned strategy appeared | C1 |
| Overconfident answer on gaps | C10 then C7 |
| Hidden contradiction | C4 |
| Fake/missing citation | C5 then C12 |
| Claim grounded without support | C12 |
| Empty evidence but fluent answer | C7 |

## Checklist

Use [`../checklists/defect-attribution.md`](../checklists/defect-attribution.md) for incidents/PRs.

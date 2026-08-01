# Modularity Freeze (018)

**Binding**: Contract **C8** + Feature **016 M0** (`specs/016-architecture-consolidation/governance/m0-freeze.md`) + [`../contracts/compatibility.md`](../contracts/compatibility.md).

## Freeze statement

No new parallel production implementations for retrieval quality or answer quality. Feature 018 extends **canonical stage owners and contracts** only. It does **not** create:

- A second retrieval path “for quality”
- A second answer generation path “for quality A/B”
- A sixth production owner named Quality / Coverage / Verification Pipeline
- Inline/runtime ownership of Feature 014 evaluation

015 dual-run Answer traffic remains **transitional** cutover only — not a permanent quality fork.

## Rejection examples

| Proposal | Reject with |
|----------|-------------|
| Parallel quality-only retrieval stack | C8 + 016 M0 |
| Merge Planner+Engine+Evidence into one mega-stage owner | C8 + single responsibility |
| Answer Generation as sole coverage authority | C10 |
| 014 faithfulness judge as request-path production owner | §18 / quality-observability + compatibility |
| Planner re-parses raw text as competing intent authority | C9 |

## Allowed

- Extending stage contracts and Quality Context/Trace under existing owners
- Domain Pack / provider extensions via published extension points (tighten-only)
- Offline evaluation feedback into configuration via Composition

# Evaluation Non-Ownership Freeze (019)

**Status**: Binding for Feature 019 architecture.

## Freeze statement

Evaluation is **not** a production RAG stage. Scoring, gating, and monitoring MUST NOT own user-facing answer generation and MUST NOT create a parallel retrieval or answer path for “evaluation mode.”

## Citations

- Feature **016** M0 freeze — no new parallel production implementations for the same concern without superseding governance ADR (`specs/016-architecture-consolidation/governance/m0-freeze.md`)
- Feature **019** research R2 — evaluation offline / CI / shadow / monitoring only
- [`../contracts/compatibility.md`](../contracts/compatibility.md) — 015/016 sole-path rules
- Feature **018** Contract C8 modularity freeze — no parallel quality/answer paths

## MUST REJECT

- Request-path mandatory evaluation as answer owner
- Dual production answer/retrieval pipelines justified by evaluation
- A new 016 sole owner named “Evaluation” or “Quality” for production traffic
- Silent PASS when Shadow path is unavailable (must SKIP)

## Allowed

- Offline golden / benchmark runs
- CI PR Core Gate consumption of offline reports
- Shadow / canary / dual-run **observation** inputs (015-compatible)
- Asynchronous production monitoring
)

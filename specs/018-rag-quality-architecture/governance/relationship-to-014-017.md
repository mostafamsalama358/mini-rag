# Relationship to Features 014–017

Normative detail: [`../contracts/compatibility.md`](../contracts/compatibility.md).

| Feature | Role relative to 018 |
|---------|----------------------|
| **014 Answer Quality** | Offline authority for coverage, faithfulness, completeness. Feedback source for configuration/pack/strategy hints. Metrics **not** redefined by 018. On disagreement, **014 wins** for release/cutover. Evaluation stays offline — never a request-path owner. |
| **015 Unified Pipeline Migration** | Dual-run → sole-path cutover vehicle. Dual-run is transitional only. Frozen external answer API not redesigned; Quality Context/Trace may exceed external fields. |
| **016 Architecture Consolidation** | Sole-owner / M0 freeze binding. 018 extends contracts; does not reassign owners or add parallel paths. Composition remains wiring authority. |
| **017 Scalability & Reliability** | Orthogonal ingest hardening. 018 must not couple answer-quality contracts to ingest job control-plane entities. Shared observability vocabulary only. |

## One-line summary

> **014** scores offline · **015** cuts over Answer · **016** owns governance · **017** hardens ingest · **018** strengthens quality contracts on the sole path.

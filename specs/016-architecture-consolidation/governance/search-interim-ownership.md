# Search Interim Retrieval Ownership

**Authority**: ADR-002  
**Status**: Interim until Search shares Answer’s Canonical Retrieval Owner

## Rule

Until Search consolidation completes, Search’s retrieval-execution consumer MUST name an **explicit interim Owner**. Silence is a Hidden Production Path (AP10 / I13).

## Current interim declaration

| Field | Value |
|-------|-------|
| Capability | Search |
| Concern | `retrieval_execution` (consumed by Search) |
| Interim owner (logical) | Documented interim Search retrieval owner (pre-share with Answer) |
| Target owner | Same Canonical Retrieval Owner as Answer |
| Forbidden | Undocumented second stack; silent ranking semantic change without validation gate |

## Exit

When M2 follow-through for Search completes: update this file and [`ownership-registry.md`](./ownership-registry.md) / [`lifecycle-registry.md`](./lifecycle-registry.md) so Search lists the shared Canonical Retrieval Owner with no interim divergence.

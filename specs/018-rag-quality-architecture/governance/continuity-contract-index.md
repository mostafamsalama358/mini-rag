# Continuity Contract Index (C1–C12)

Normative detail: [`../contracts/quality-continuity.md`](../contracts/quality-continuity.md) and sibling contracts.

| ID | Name | One-line rule | Primary contract file |
|----|------|---------------|----------------------|
| C1 | Strategy Alignment | Engine executes plan strategies; no silent unplanned strategy-family substitution | [`retrieval-quality.md`](../contracts/retrieval-quality.md) |
| C2 | Filter Pushdown Continuity | Plan filters applied or explicitly residual/unapplied before Evidence Pack | [`retrieval-quality.md`](../contracts/retrieval-quality.md) |
| C3 | Deduplication Ladder | Engine identity → Evidence content → Context safety-net; preserve citation attribution | [`evidence-and-context-quality.md`](../contracts/evidence-and-context-quality.md) |
| C4 | Conflict Continuity | Candidates → disclosure-ready groups → user disclosure; omission ≠ agreement | [`evidence-and-context-quality.md`](../contracts/evidence-and-context-quality.md) |
| C5 | Citation Continuity | Evidence → Chunk → Document → Source → Citation intact for included/cited material | [`answer-grounding.md`](../contracts/answer-grounding.md) |
| C6 | Token Efficiency | Prefer early filter/dedup/policy compression over citation-breaking truncation | [`evidence-and-context-quality.md`](../contracts/evidence-and-context-quality.md) |
| C7 | Hallucination Prevention Chain | Each stage contributes; no fabricated certainty | [`answer-grounding.md`](../contracts/answer-grounding.md) |
| C8 | Modularity Freeze | No parallel quality/retrieval/answer path; no sixth “quality” owner | [`compatibility.md`](../contracts/compatibility.md) |
| C9 | Understood Query Authority | No competing re-parse; clarification/degradation propagate | [`query-understanding-handoff.md`](../contracts/query-understanding-handoff.md) |
| C10 | Coverage & Missing-Evidence Continuity | complete/partial/missing flow Evidence → Quality Context → Answer; 014 offline authority | [`evidence-and-context-quality.md`](../contracts/evidence-and-context-quality.md) |
| C11 | Quality Context / Trace Continuity | Enrich/append only; no erase of upstream ownership | [`quality-observability.md`](../contracts/quality-observability.md) |
| C12 | Claim-Level Grounding Continuity | Ungrounded claims never presented as grounded | [`answer-grounding.md`](../contracts/answer-grounding.md) |

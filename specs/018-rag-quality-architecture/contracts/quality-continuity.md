# Contract: Cross-Stage Quality Continuity

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative summary of Contracts C1–C12 from [spec.md](../spec.md). Detail lives in sibling contracts; this file is the continuity checklist for architecture review.

---

## Purpose

Prevent quality from being “dropped on the floor” between stage handoffs without merging stages or adding parallel pipelines.

---

## Contracts

| ID | Name | Normative rule (short) |
|----|------|------------------------|
| C1 | Strategy Alignment | Engine executes plan strategies; no silent unplanned strategy-family substitution |
| C2 | Filter Pushdown Continuity | Plan filters applied or explicitly residual/unapplied before Evidence Pack |
| C3 | Deduplication Ladder | Engine identity → Evidence content → Context safety-net; preserve citation attribution |
| C4 | Conflict Continuity | Candidates → disclosure-ready groups → user disclosure; omission ≠ agreement |
| C5 | Citation Continuity | Evidence → Chunk → Document → Source → Citation intact for included/cited material |
| C6 | Token Efficiency | Prefer early filter/dedup/policy compression over citation-breaking truncation |
| C7 | Hallucination Prevention Chain | Each stage contributes; no fabricated certainty (§14) |
| C8 | Modularity Freeze | No parallel quality/retrieval/answer path; no sixth “quality” owner |
| C9 | Understood Query Authority | No competing re-parse; clarification/degradation propagate |
| C10 | Coverage & Missing-Evidence Continuity | complete/partial/missing flow Evidence → Quality Context → Answer; 014 offline authority |
| C11 | Quality Context / Trace Continuity | Enrich/append only; no erase of upstream ownership |
| C12 | Claim-Level Grounding Continuity | Ungrounded claims never presented as grounded |

---

## Ownership freeze (binding)

Quality improvements MUST extend canonical owners from Feature 016. They MUST NOT:

- Merge Planner + Engine + Evidence into one production owner
- Create a second retrieval or answer path
- Move coverage ownership into Answer Generation
- Make offline evaluation a request-path owner

---

## Acceptance

A proposed design fails continuity review if it violates any row above or cannot attribute a bad-answer vignette to the earliest broken contract.

---

## Related contracts

- [query-understanding-handoff.md](./query-understanding-handoff.md)
- [retrieval-quality.md](./retrieval-quality.md)
- [evidence-and-context-quality.md](./evidence-and-context-quality.md)
- [answer-grounding.md](./answer-grounding.md)
- [quality-observability.md](./quality-observability.md)
- [compatibility.md](./compatibility.md)

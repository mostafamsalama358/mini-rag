# Quality Context & Trace Registry (018)

Normative: [`../contracts/quality-observability.md`](../contracts/quality-observability.md), spec §§16/20, Contract **C11**.

Neither artifact replaces stage outputs (Understood Query, Plan, Retrieval Result, Evidence Pack, Context, Answer Result).

---

## Quality Context (cumulative state)

| Field / cluster | Enriching stage | Overwrite rule |
|-----------------|-----------------|----------------|
| ambiguity | Query Understanding | Upstream-owned; others must not overwrite |
| parse_confidence | Query Understanding | Upstream-owned |
| clarification_required | Query Understanding | Upstream-owned |
| retrieval_confidence | Retrieval | Additive / namespaced |
| filter_residual | Retrieval | Additive / namespaced |
| degradation_history | Any | Append-only list |
| coverage / sufficiency | Evidence | Upstream-owned for sufficiency |
| evidence_confidence | Evidence | Additive / namespaced |
| conflict_summary | Evidence → Context | Context may add budget omission notes |
| citation_completeness | Context | Context-owned |
| budget_usage | Context | Context-owned |
| grounding_status | Answer Generation | Answer-owned |
| no_answer_condition | Answer Generation | Answer-owned |

**Rule**: Enrichments are additive or namespaced. **Upstream overwrite is forbidden (C11).**

---

## Quality Trace (append-only sections)

| Section | Producer | Required diagnostic contents (architectural) |
|---------|----------|-----------------------------------------------|
| Plan Trace | Retrieval Plan | Strategy justifications, clarification/degradation |
| Retrieval Trace | Retrieval | Per-leg counts, normalization notes |
| Expansion Trace | Retrieval | Variants used; policy bounds |
| Fusion Trace | Retrieval | Merge participation |
| Rerank Trace | Retrieval | Participation or explicit disablement/degradation |
| Evidence Trace | Evidence | Dedup, coverage/sufficiency, conflict candidates, quality signals |
| Context Trace | Context | Priority selection, compression, budget omissions, citation completeness |
| Generation Trace | Answer Generation | Prompt version, generative vs no-answer path |
| Verification Trace | Answer Generation | Claim outcomes, unsupported flags, citation resolution |

**Rule**: Stages append; they do not erase upstream sections. Disabled rerank MUST appear as disablement — not invented scores.

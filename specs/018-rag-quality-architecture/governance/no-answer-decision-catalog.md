# No-Answer Decision Catalog (018)

From spec §15. **Decision owner**: Answer Generation. Upstream stages own signal honesty.

| Condition | Primary signal source | Architectural expectation |
|-----------|----------------------|---------------------------|
| no_evidence | Engine/Evidence empty | Explicit no-answer; no generative fill-in |
| weak_evidence | Evidence quality / confidence | Limited-answer or no-answer; no overconfidence |
| conflicting_evidence | Context conflicts | Disclose conflict; may refuse single definitive answer |
| partial_evidence | Missing-evidence / coverage | Answer only supported facets; state gaps |
| ambiguous_query | Understood Query / Planner | Clarification or non-definitive posture |
| out_of_domain | Query Understanding / Planner | Unsupported / out-of-scope posture |
| restricted_answer | Policy / Domain Pack constraints via Application | Refuse or constrain per policy without fabricating |

When none apply and evidence supports claims: condition may be `none` with normal grounded answer path.

# Contract: Evaluation Bridge (Feature 019)

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22  
**Authority**: Feature 019 owns implementation; 020 owns recommend metric *requirements*

---

## Separation of duties

| 020 | 019 |
|-----|-----|
| Defines recommend metric catalog & success intent | Implements scorers, judges, profiles, gates, run metadata |
| Defines RecommendEvalCase shape needs | Dataset/benchmark governance & freeze |
| Forbids request-path eval ownership | Offline / shadow / monitoring modes only |

## Metric catalog (required for recommend profile coverage)

| Metric | Intent |
|--------|--------|
| Recall@K | Allow-listed products in top-K |
| Precision@K | Top-K relevance fraction |
| MRR | First relevant rank quality |
| nDCG | Graded list quality when labels exist |
| Safety Precision | Correctness of safety actions taken |
| Safety Recall | Coverage of required exclude/demote actions |
| False Recommendation Rate | Out-of-corpus / forbidden / fabricated recommends |
| Clarification Rate | Clarification/limited-coverage on designated items |
| Corpus-Boundedness | All recommended products in corpus |
| Recommendation Diversity | Non-redundant identity/therapy spread per policy |

## Profile expectation (architecture)

1. A pharmacy **recommendation evaluation profile** MUST exist under 019 before “recommend ready” ship claims (spec SC-008).
2. Gates MUST distinguish taxonomy/retrieval vs ranking vs safety vs generation failures.
3. Concrete numeric thresholds are **ops/profile policy**, not fixed in 020 architecture contracts (except success criteria already stated as measurable targets in spec.md for acceptance intent).

## Non-goals

- No production evaluation stage inside Answer.
- No duplicate metric system owned by 020.

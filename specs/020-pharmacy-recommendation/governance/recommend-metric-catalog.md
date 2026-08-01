# Recommend Metric Catalog (020 → 019)

Feature **019 implements** scorers/profiles/gates. Feature **020** defines the pharmacy recommend catalog.

| Metric | Intent | Attribution bucket (primary) |
|--------|--------|------------------------------|
| Recall@K | Allow-listed products in top-K | Retrieval / taxonomy |
| Precision@K | Top-K relevance fraction | Ranking / retrieval |
| MRR | First relevant rank | Ranking |
| nDCG | Graded list quality | Ranking |
| Safety Precision | Correctness of safety actions | Safety filter |
| Safety Recall | Required exclude/demote coverage | Safety filter |
| False Recommendation Rate | Out-of-corpus / fabricated | Generation / corpus bound |
| Clarification Rate | Clarification on ambiguous items | Query understanding / taxonomy |
| Corpus-Boundedness | All recommended products in corpus | Policy / generation |
| Recommendation Diversity | Non-redundant identity/therapy spread | Identity / ranking |

Defect buckets: taxonomy/tag miss · retrieval miss · ranking error · safety-filter error · generation/explanation hallucination.

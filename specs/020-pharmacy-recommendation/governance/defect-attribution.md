# Defect Attribution — Recommend Mode

| Symptom | Likely bucket | Primary owner concern |
|---------|---------------|------------------------|
| Wrong clinical bucket / missed tag | taxonomy/tag miss | Query Understanding / Domain Pack |
| Tags correct but products missing from retrieval | retrieval miss | Retrieval Engine |
| Relevant products retrieved but poor order | ranking error | Retrieval (ranking signals) / Policy |
| Unsafe product promoted | safety-filter error | Safety filter / Pack safety model |
| Invented brand / hidden-score story | generation/explanation hallucination | Answer Generation |
| Out-of-corpus recommend | Corpus-Boundedness / False Recommendation | Policy + Answer |

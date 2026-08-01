# Architecture Review Checklist — 020 Pharmacy Recommendation

- [x] ADR-020-001 present: capability only; no Service/API/parallel path/new owner
- [x] Frozen `/answer` contract unchanged (015)
- [x] Logical flow documented as non-pipeline
- [x] Ranking signals named; weights policy-owned
- [x] Safety model extensible; v1 subset OK
- [x] Symptom Taxonomy controlled (not flat dict-only)
- [x] Candidate explainability via RecommendationTrace
- [x] Product Identity Rules present
- [x] Explanation Policy evidence-only
- [x] Evaluation metrics catalog; 019 owns runners
- [x] M0 freeze respected

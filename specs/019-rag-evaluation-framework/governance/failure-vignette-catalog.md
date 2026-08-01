# Failure Vignette Catalog (019)

| VignetteId | Symptom | Failed Metrics | Primary Owner | Error Category | Theme |
|------------|---------|----------------|---------------|----------------|-------|
| V-RET-001 | Required relevant chunks absent from ranked results | Recall, Completeness | Retrieval Engine | Retrieval Failure | ranking/miss |
| V-RET-002 | Relevant item present but ranked last among many distractors | MRR, NDCG | Retrieval Engine | Retrieval Failure | worse-ranking |
| V-RET-003 | High Precision but misses half of labeled relevants at cutoff | Recall | Retrieval Engine | Retrieval Failure | ranking/miss |
| V-RET-004 | Shuffled ranking of same candidates vs good ranking | NDCG, MRR | Retrieval Engine | Retrieval Failure | worse-ranking |
| V-ADV-001 | Answer asserts fabricated entity/number not in cited evidence | Faithfulness, Hallucination Rate, Groundedness | Answer Generation | Grounding Failure | fabricated-entity |
| V-ADV-002 | Claim cites resolved id that does not support the claim | Citation Accuracy | Answer Generation | Citation Failure | mismatched-citation |
| V-ADV-003 | Assertive answer with empty citation map claimed as grounded | Groundedness, Citation Accuracy | Answer Generation | Citation Failure | mismatched-citation |
| V-ADV-004 | Correct labeled no-answer when evidence missing | (none — not hallucination) | Answer Generation | Generation Failure | correct-no-answer |
| V-ADV-005 | Citation-washed fluent answer with unsupported spans | Hallucination Rate, Faithfulness | Answer Generation | Grounding Failure | fabricated-entity |
| V-PLN-001 | Plan omits required filter constraint from labels | Plan Fidelity | Retrieval Planner | Planner Failure | omitted-constraint |
| V-PLN-002 | Plan re-parses raw text contrary to Understood Query labels | Plan Fidelity, Strategy Alignment | Retrieval Planner | Planner Failure | re-parse |
| V-PLN-003 | Strategy family selected without capability justification | Strategy Alignment | Retrieval Planner | Planner Failure | omitted-constraint |
)

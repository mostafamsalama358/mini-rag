# Evaluation Run Metadata Catalog (019)

From [`../data-model.md`](../data-model.md) / [`../contracts/evaluation-pipeline.md`](../contracts/evaluation-pipeline.md).

| Metadata field | Purpose |
|----------------|---------|
| run id | Stable identity |
| commit | Source revision under test |
| branch | Development line |
| release | Release identifier when applicable |
| prompt version | Prompt lineage affecting generation |
| embedding version | Embedding artifact/version identity |
| reranker version | Reranker artifact/version identity |
| retriever version | Retriever configuration/version identity |
| planner version | Planner configuration/version identity |
| model version | Generation model identity |
| configuration fingerprint | Aggregate config fingerprint |
| dataset version | Frozen dataset identity |
| benchmark version | Optional frozen benchmark pin |
| profile | Evaluation profile used |
| experiment role | Baseline / Candidate / Champion / Challenger / Shadow / Canary |
| judge type(s) / version(s) | Judge Layer provenance |
| cost unit policy | Declared Cost accounting units |
| gate decision | Pass / Fail / Skip with reasons |

Blocking profiles SHOULD require the subset needed for their reproducibility claims.
)

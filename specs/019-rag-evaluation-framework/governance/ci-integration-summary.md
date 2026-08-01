# CI Integration Summary (019)

Normative detail: [`../contracts/evaluation-pipeline.md`](../contracts/evaluation-pipeline.md).

## Contract (not a product choice)

| Requirement | Rule |
|-------------|------|
| Machine-readable report | Structured artifact per Evaluation Run |
| Fail signal | Non-zero / failing signal when **PR Core Gate** fails |
| Report contents | run id, dataset/benchmark versions, configuration fingerprint (+ related metadata), aggregates, composites (if any), failed item ids, error taxonomy summary, gate decision, experiment role |
| Baseline compare | Ability to diff against stored baseline/champion |
| Non-serving | Invokable without serving user traffic |
| Secrets / PII | Core Golden CI MUST NOT require production secrets or raw PII |

Concrete CI vendors, workflow files, and schedules are **out of architecture scope**.
)

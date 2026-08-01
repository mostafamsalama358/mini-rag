# Experiment Role Catalog (019)

Normative detail: [`../contracts/experiment-comparison.md`](../contracts/experiment-comparison.md).

| Role | Meaning |
|------|---------|
| Baseline | Reference for deltas |
| Candidate | Proposed change under evaluation |
| Champion | Accepted production-quality reference for a release line |
| Challenger | Contender seeking to replace champion via gates + review |
| Shadow | Non-user-visible evaluation on live-like inputs |
| Canary | Limited-exposure observation role for evaluation comparison |

## Rules

1. Comparisons pin compatible frozen dataset/benchmark versions (or explicit evolution bridge).
2. Champion replacement is governance/evaluation outcome — not automatic single-metric win.
3. Shadow/Canary MUST NOT imply a second user-visible answer owner (015/016).
4. Traffic shifting / deployment mechanics are out of scope.
)

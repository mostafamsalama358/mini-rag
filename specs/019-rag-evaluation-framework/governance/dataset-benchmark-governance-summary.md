# Dataset & Benchmark Governance Summary (019)

Normative detail: [`../contracts/dataset-benchmark-governance.md`](../contracts/dataset-benchmark-governance.md).

## Lifecycle

Draft → In Review → Approved → Frozen → Retired / Superseded

## Binding rules

| Concern | Rule |
|---------|------|
| Approval | Blocking tiers require explicit approval before freeze |
| Freeze | **No in-place mutation** of Frozen dataset/benchmark content; fixes ⇒ new version |
| Lineage | Each version declares predecessor + derivation notes |
| Changelog | Required on version bump |
| Compatibility | Schema incompat ⇒ fail closed for blocking profiles |
| Reproducibility | Run citing version X must interpret against frozen X + run metadata + judge version |
| Comparability | Cross-release benchmark compare requires same frozen version OR explicit evolution bridge |

## Responsibilities

| Role | Responsibility |
|------|----------------|
| Dataset curator | Draft, changelog, lineage |
| Approver | Approve/reject freeze; review gate-loosening |
| Evaluation architect | Schema fitness, tier/profile binding |
| Domain Pack owner | Domain label correctness |
| Release owner | Ensure Release profile pins approved freezes |
)

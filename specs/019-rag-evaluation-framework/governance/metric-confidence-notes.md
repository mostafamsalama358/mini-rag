# Metric Confidence Notes (019)

Optional fields on metric judgments (from [`../contracts/metric-system.md`](../contracts/metric-system.md)):

| Field | Purpose |
|-------|---------|
| confidence | Optional certainty of the judgment |
| judge version | Identity of the judge configuration |
| agreement | Optional multi-judge agreement signal |
| evaluation provenance | Trace of how the score was produced |

**Rule**: Absence is valid. Missing confidence ≠ failure. Supports future multi-judge systems without changing Evaluation Run / Item Result contracts.
)

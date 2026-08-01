# Offline Feedback Loop (018)

Normative: [`../contracts/quality-observability.md`](../contracts/quality-observability.md) §D, Feature **014**.

```text
Production / shadow answers
        ↓
Offline Evaluation (014)
  — coverage, faithfulness, completeness
  — stage metrics as diagnostics only
        ↓
Configuration / policy feedback
  — thresholds, Domain Pack profiles, strategy registry hints, budget policies
        ↓
Composition wires runtime stages
  — ownership unchanged (016)
```

## Rules

1. Evaluation remains **offline** — never a request-path owner.
2. Feedback MUST NOT create parallel retrieval/answer paths.
3. On disagreement between stage heuristics and 014 gates, **014 wins** for release/cutover.
4. 018 stage metrics do **not** redefine 014 golden definitions ([`stage-quality-metrics.md`](./stage-quality-metrics.md)).

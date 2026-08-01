# Relationship to Features 014–018 (019)

Normative detail: [`../contracts/compatibility.md`](../contracts/compatibility.md).

| Feature | Stance |
|---------|--------|
| **014 Answer Quality** | Semantic seed for coverage / Faithfulness / Completeness. Definitions preserved. **019** is evaluation architecture authority. |
| **015 Unified Pipeline** | Shadow/dual-run/canary may supply evaluation inputs. No second answer owner. Unavailable shadow ⇒ SKIP, not PASS. Frozen external `/answer` API unchanged. |
| **016 Consolidation** | Sole-owner + M0 freeze binding. Metric Primary Owners map to existing concerns. Latency/Cost ops attribution is evaluation-only. |
| **018 Quality Architecture** | Stage diagnostics feed evaluation. On release disagreement, **019 gates win**. Prefer Quality Context / Trace enrichment. No sixth production quality owner. |
| **017 Scalability** | Orthogonal ingest reliability. Evaluation MUST NOT depend on ingest job control-plane entities. |

## Feedback loop (architectural)

```text
Production / shadow answers
        →
Offline / profile evaluation (019; 014 semantics preserved)
        →
Configuration / policy feedback
        →
Composition wires runtime stages (016 ownership unchanged)
```
)

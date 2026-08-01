# Judge Layer Registry (019)

Normative detail: [`../contracts/judge-layer.md`](../contracts/judge-layer.md).

| Judge type | Role |
|------------|------|
| Rule Judge | Deterministic rule / label matching |
| LLM Judge | Model-assisted judgment under same metric semantics |
| Human Judge | Human adjudication / audit / escalation |
| Hybrid Judge | Composition with declared precedence policy |

## Metric stability (binding)

Changing judge type MUST NOT redefine canonical metric identity or meaning. Faithfulness remains Faithfulness across Rule / LLM / Human / Hybrid. **Judge-specific parallel metric names for the same concept are forbidden.**

## Provenance

Runs MUST be able to record judge type(s) and judge version(s). Optional confidence / agreement fields: see [`metric-confidence-notes.md`](./metric-confidence-notes.md).

## Hybrid precedence (policy shape)

Hybrid judges declare which judgment wins on conflict. Unresolved required judgments escalate rather than silent PASS under blocking profiles.

## Non-ownership

Judges are evaluation components — not production pipeline stages.
)

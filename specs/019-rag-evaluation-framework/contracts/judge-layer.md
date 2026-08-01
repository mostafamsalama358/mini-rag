# Contract: Judge Layer

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative interchangeability rules for evaluation judges.

---

## Purpose

Allow Rule, LLM, Human, and Hybrid judgment producers behind stable metric contracts.

---

## Judge types

| Type | Role |
|------|------|
| Rule Judge | Deterministic rule / label matching |
| LLM Judge | Model-assisted judgment under same metric semantics |
| Human Judge | Human adjudication / audit / escalation |
| Hybrid Judge | Composition with declared precedence policy |

---

## Normative rules

1. **Metric stability** — Changing judge type MUST NOT redefine canonical metric identity or meaning (Faithfulness remains Faithfulness, etc.).
2. **Provenance** — Runs MUST be able to record judge type(s) and judge version(s) for scored metrics.
3. **Optional confidence** — Judges MAY emit confidence and agreement; consumers treat absence as unknown.
4. **Profile policy** — A profile MAY require a designated judge class for a blocking metric; that is architectural policy, not an implementation prescription.
5. **Hybrid conflict** — Hybrid precedence is declared policy; unresolved required judgments escalate rather than silent PASS under blocking profiles.
6. **Non-ownership** — Judges are evaluation components; they are not production pipeline stages and do not own retrieval or answer generation.
7. **Out of scope** — Judge prompts, models, heuristics, calibration formulas, and vendor selection are non-normative here.

---

## Acceptance

Contract review fails if:

- A design introduces judge-specific parallel metric names for the same concept
- Blocking profiles can PASS when a required judge is unavailable without explicit Skip/Fail policy
- Judge Layer is used to justify a second production answer path
)

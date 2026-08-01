# Contract: Explainability and Recommendation Trace

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22  
**Related**: Feature 018 Quality Context / Trace

---

## Candidate Explainability (operator)

For each candidate considered in recommend-mode, diagnostics/Trace MUST make available:

| Attribute | Meaning |
|-----------|---------|
| Matched Indications | Taxonomy/tag hits vs NeedFrame |
| Retrieved Evidence | Evidence pointers supporting inclusion |
| Safety Outcome | pass/demote/exclude/unknown + dimensions |
| Rank Contribution | Which ranking signals drove relative order |

## Surfaces

1. **Operator / Quality Context / Recommendation Trace** — allowed diagnostic surface (018-aligned).
2. **End-user `/answer` text** — Explanation Policy only; MUST NOT require hidden score dumps or internal prompts.
3. MUST NOT introduce a breaking public API field solely for Trace in v1.

## Defect attribution

Trace MUST be sufficient for 019 attribution buckets at least: taxonomy/tag miss, retrieval miss, safety-filter error, ranking error, generation/explanation hallucination.

## Logging

Structured logs at recommend-mode boundaries include correlation id / project id; no secrets or unnecessary PII; avoid logging full hidden weight tables at info level in production if sensitive—Trace access follows existing diagnostic controls.

# Continuity Worked Examples (018)

## Example A — Partial evidence + budget pressure

1. **Query Understanding**: intent clear; entities grounded; clarification_required=false.
2. **Planner**: strategies justified; filters declared.
3. **Engine**: candidates returned; filters applied; calibrated scores present; Rerank Trace OK.
4. **Evidence**: CoverageAssessment sufficiency=`partial`; facet_gaps lists missing facet; Quality Context updated.
5. **Context**: Priority keeps primary + conflict; drops redundant; budget omission may further degrade coverage — recorded in Context Trace / Quality Context (not claimed as upstream complete).
6. **Answer**: NoAnswerDecision condition=`partial_evidence` (or limited answer stating gaps); unsupported facets not marked grounded (C12).

## Example B — Disabled rerank honesty

1. Reranking disabled by configuration.
2. **Rerank Trace** records disablement/degradation.
3. Fusion order remains valid handoff; no invented rerank scores (C11).
4. Downstream may see quality impact; contracts remain honest.

## Example C — Conflict + budget omission

1. **Evidence**: ConflictCandidate category=`semantic` for two items.
2. **Context**: One side dropped for budget → ConflictGroup `resolution=omission`.
3. **Answer**: MUST NOT claim sources agreed; disclose remaining conflict or limited posture (C4).

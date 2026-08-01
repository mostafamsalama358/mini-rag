# Quality Entity Catalog (018)

Architectural entities from [`../data-model.md`](../data-model.md). Physical type names are non-normative.

| Entity | Purpose | Key fields / rules | Owner concern |
|--------|---------|-------------------|---------------|
| UnderstoodQuery | Canonical parse handoff to Planner | intent, ambiguity, confidence, entities, constraints, clarification_required, degradation_reason | Query Understanding |
| RetrievalPlan | What to retrieve + justified strategies | StrategySelection[], FilterConstraint[], degradation, budget_hints | Retrieval Plan |
| StrategyRegistryEntry | Catalog entry for selectable strategies | strategy_id, capabilities, compatibility_notes | Retrieval Plan |
| CandidateLifecycle | Engine progression through retrieval steps | retrieval→…→calibration→selection | Retrieval |
| CalibratedScoreSet | Comparable scores + provenance | calibrated_score, provenance, degraded | Retrieval |
| RetrievalResult | Handoff candidates to Evidence | selected candidates, traces | Retrieval |
| EvidencePack | Organized evidence set | items, coverage, sufficiency, conflict candidates | Evidence |
| EvidenceItem | Single evidence unit + quality signals | text, attribution, quality dimensions | Evidence |
| EvidenceQualitySignals | authority/freshness/completeness/semantic_coverage/locality/confidence | unknown allowed | Evidence |
| CoverageAssessment | Runtime coverage diagnostic | summary, facet_gaps, sufficiency | Evidence |
| EvidenceSufficiencyState | complete \| partial \| missing | explicit; never hidden | Evidence |
| ConflictCandidate | Categorized disagreement candidate | category, evidence_ids | Evidence |
| Context | Budgeted prompt-ready context | blocks, citation map, conflicts | Context |
| ContextPriorityClass | conflict→…→redundant | selection preference | Context |
| ContextBlock | Included (possibly compressed) block | priority_class, citation_id, compressed | Context |
| CitationChain | Evidence→Chunk→Document→Source→Citation | required for included blocks | Context / Answer |
| ConflictGroup | Disclosure-ready conflict | category, resolution (omission ≠ agreement) | Context |
| AnswerResult | User-facing answer + grounding outcomes | claims, citations, no_answer_decision | Answer Generation |
| ClaimGroundingOutcome | Per-claim grounding status | grounded requires non-empty support | Answer Generation |
| NoAnswerDecision | Architectural no-answer condition | condition enum from §15 | Answer Generation |
| QualityContext | Cumulative accompanying quality state | enrich, do not overwrite upstream | All stages (namespaced) |
| QualityTrace | Append-only sectioned diagnostics | nine sections §16 | Producing stages |
| StageQualityMetric | Architecture-level diagnostic metric | must not redefine 014 goldens | Stage + Offline Evaluation |
| ExtensionPoint | Published stage extension surface | tighten-only; Composition wires | Stage + Composition |

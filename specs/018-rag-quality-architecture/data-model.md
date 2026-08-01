# Data Model: RAG Quality Architecture

**Feature**: 018-rag-quality-architecture | **Date**: 2026-07-18

This model describes **architectural quality entities and contracts**, not database tables, wire codecs, or runtime class names. Physical persistence and type names are non-normative.

---

## Entity Overview

```text
UnderstoodQuery
  └── consumed by RetrievalPlan

RetrievalPlan
  └── StrategySelection[] (ordered, justified)
  └── FilterConstraint[]
  └── drives CandidateLifecycle

CandidateLifecycle
  └── produces RetrievalResult (selected candidates + calibrated scores)

EvidencePack
  └── EvidenceItem[] (+ EvidenceQualitySignals)
  └── CoverageAssessment
  └── EvidenceSufficiencyState
  └── ConflictCandidate[]

Context
  └── ContextBlock[] (priority-selected, possibly compressed)
  └── CitationMap (CitationChain links)
  └── ConflictGroup[]

AnswerResult
  └── ClaimGroundingOutcome[]
  └── Citation[]
  └── NoAnswerDecision

QualityContext          # cumulative accompanying state
QualityTrace            # append-only sectioned diagnostics
```

Stage outputs remain primary. QualityContext / QualityTrace accompany; they do not replace.

---

## UnderstoodQuery

Canonical Query Understanding output.

| Field | Rules |
|-------|-------|
| `parsed_intent` | Required canonical intent/operation |
| `ambiguity` | Required; whether competing interpretations remain |
| `confidence` | Required parse/grounding confidence signal |
| `extracted_entities` | Grounded entities only; no fabrications |
| `extracted_constraints` | Filterable/scoping constraints |
| `clarification_required` | Boolean; when true, planning must not pretend certainty |
| `degradation_reason` | Required when degraded/unsupported/partial |
| `schema_version` | Major version validated by consumers |

**Validation**: Planner MUST NOT invent conflicting intent by re-parsing raw text (Contract C9).

---

## RetrievalPlan

Planner output.

| Field | Rules |
|-------|-------|
| `strategies` | Ordered list of StrategySelection |
| `filter_constraints` | Eligible for Engine pushdown |
| `clarification_required` | Propagated/derived from UnderstoodQuery |
| `degradation_reason` | Explicit when strategy set narrowed/conservative |
| `budget_hints` | Advisory candidate/evidence ceilings |
| `schema_version` | Major version validated by Engine |

### StrategySelection

| Field | Rules |
|-------|-------|
| `strategy_id` | Must exist in Strategy Registry |
| `justification` | Non-empty; ties to parse signals + capabilities |
| `order_index` | Deterministic total order |

### StrategyRegistryEntry (Planner-owned catalog concept)

| Field | Rules |
|-------|-------|
| `strategy_id` | Stable id |
| `capabilities` | Capability flags (dense/sparse/metadata/filter-pushdown/expansion/locality) |
| `compatibility_notes` | Constraints vs other strategies |

---

## CandidateLifecycle / RetrievalResult

Engine-owned progression and handoff.

| Lifecycle step | Output concept |
|----------------|----------------|
| Candidate Retrieval | Raw per-leg candidates |
| Candidate Normalization | Common candidate contract |
| Filter Pushdown | Applied + residual filter records |
| Query Expansion | Expansion variants used |
| Fusion | Merged pool |
| Identity Deduplication | Identity-collapsed pool |
| Reranking | Optionally reordered pool |
| Score Calibration | CalibratedScoreSet + provenance |
| Candidate Selection | Budget-capped RetrievalResult |

### CalibratedScoreSet

| Field | Rules |
|-------|-------|
| `candidate_id` | Required |
| `calibrated_score` | Comparable downstream signal |
| `provenance` | Which heterogeneous signals contributed |
| `degraded` | True if calibration/rerank passthrough |

**Validation**: Silent filter loss forbidden (C2). Unplanned strategy family substitution forbidden without traced degradation (C1).

---

## EvidencePack

Evidence Orchestrator output.

### EvidenceItem

| Field | Rules |
|-------|-------|
| `evidence_id` | Stable within pack |
| `text` | Non-fabricated |
| `attribution` | Chunk/document/source links for citation chain |
| `quality` | EvidenceQualitySignals |
| `conflict_candidate_refs` | Optional |

### EvidenceQualitySignals

| Dimension | Rules |
|-----------|-------|
| `authority` | Value or `unknown` |
| `freshness` | Value or `unknown` |
| `completeness` | Value or `unknown` |
| `semantic_coverage` | Value or `unknown` |
| `locality` | Value or `unknown` |
| `confidence` | Value or `unknown` |

Absence MUST be explicit `unknown`, not implicit high quality.

### CoverageAssessment

| Field | Rules |
|-------|-------|
| `summary` | Stakeholder-readable coverage judgment |
| `facet_gaps` | Facets of the request not adequately supported |
| `sufficiency` | `complete` \| `partial` \| `missing` |

### EvidenceSufficiencyState

Enum: `complete` | `partial` | `missing`.

**Validation**: Must be explicit in pack metadata and Quality Context (C10). Answer Generation must not invent completeness.

### ConflictCandidate

| Field | Rules |
|-------|-------|
| `category` | `semantic` \| `temporal` \| `authority` \| `version` \| `duplicate_disagreement` |
| `evidence_ids` | ≥ 2 |
| `subject_ref` | What the disagreement is about |

---

## Context

Context Builder output.

### ContextPriorityClass

Enum (selection preference high→low):  
`conflict` | `primary` | `supporting` | `contextual` | `background` | `redundant`

### ContextBlock

| Field | Rules |
|-------|-------|
| `block_id` | Stable |
| `evidence_id` | Source evidence |
| `priority_class` | Required |
| `text` | Possibly compressed |
| `compressed` | Boolean |
| `token_count` | Required |
| `citation_id` | Must exist in CitationMap |

### CitationMap / CitationChain

Logical links for each included block:

`Evidence → Chunk → Document → Source → Citation`

| Link | Required for included blocks |
|------|------------------------------|
| evidence_id | Yes |
| chunk_id | Yes (or explicit unknown with degradation — preferred yes) |
| document_id | Yes |
| source_id | Yes |
| citation_id | Yes |

**Validation**: Dropped blocks leave no dangling citations. Compression preserves chain for retained blocks (C5).

### ConflictGroup

| Field | Rules |
|-------|-------|
| `category` | From conflict model |
| `evidence_ids` / `block_ids` | Survivors |
| `resolution` | `null` (both survive) \| `omission` \| other non-agreement labels |

Omission MUST NOT be labeled agreement (C4).

### CompressionRecord

| Field | Rules |
|-------|-------|
| `block_id` | Required |
| `compressible_class` | `compressible` \| `non_compressible` |
| `outcome` | `compressed` \| `included_raw` \| `dropped` |
| `preservation` | Citation / conflict / grounding anchors retained when included |

---

## AnswerResult

Answer Generation output (includes logical verification outcomes).

### ClaimGroundingOutcome

| Field | Rules |
|-------|-------|
| `claim` | Atomic claim text/identity |
| `status` | `grounded` \| `ungrounded` \| `limited` |
| `supporting_evidence_ids` | Required non-empty when `grounded` |
| `citation_ids` | Subset of Context citation map when grounded |

**Validation**: `grounded` with empty support is illegal (C12).

### NoAnswerDecision

| Field | Rules |
|-------|-------|
| `condition` | `no_evidence` \| `weak_evidence` \| `conflicting_evidence` \| `partial_evidence` \| `ambiguous_query` \| `out_of_domain` \| `restricted_answer` \| `none` |
| `no_answer` | Boolean |
| `limitations_note` | Required when limited/partial/conflict |

### AnswerResult fields (architectural)

| Field | Rules |
|-------|-------|
| `answer` | User-visible text (or explicit no-answer message) |
| `citations` | Resolved only from Context map |
| `conflicts_disclosed` | True when surviving conflicts disclosed |
| `claim_outcomes` | Claim-level grounding results |
| `no_answer_decision` | Required |
| `prompt_version` | Required when generative path used |

---

## QualityContext

Cumulative accompanying quality metadata.

| Field cluster | Enriching stage(s) | Overwrite rule |
|---------------|--------------------|----------------|
| Ambiguity / parse confidence / clarification | Query Understanding | Upstream-owned; others must not overwrite |
| Retrieval confidence / filter residual / degradation | Engine | Additive/namespaced |
| Coverage / sufficiency / evidence confidence | Evidence | Upstream-owned for sufficiency |
| Conflict summary | Evidence → Context | Context may add budget omission notes |
| Citation completeness / budget usage | Context | Context-owned |
| Grounding status / no-answer condition | Answer | Answer-owned |
| Degradation history | Any | Append-only list |

**Validation**: No stage overwrites another stage’s ownership namespace (C11).

---

## QualityTrace

Append-only diagnostics.

| Section | Producer |
|---------|----------|
| Plan Trace | Planner |
| Retrieval Trace | Engine |
| Expansion Trace | Engine |
| Fusion Trace | Engine |
| Rerank Trace | Engine |
| Evidence Trace | Evidence |
| Context Trace | Context |
| Generation Trace | Answer |
| Verification Trace | Answer (logical verification) |

**Validation**: Sections are append-only; upstream sections are not erased.

---

## StageQualityMetric (architectural)

| Field | Rules |
|-------|-------|
| `stage` | Query Understanding \| Planner \| Engine \| Evidence \| Context \| Answer |
| `metric_id` | Stable id from spec §17 |
| `purpose` | Diagnostic / offline-aligned |
| `offline_authority` | Must not redefine 014 golden metrics |

---

## ExtensionPoint

| Field | Rules |
|-------|-------|
| `stage` | Owning stage |
| `extension_kind` | Pack profile \| provider adapter \| policy profile |
| `allowed_effects` | May tighten quality |
| `forbidden_effects` | Must not weaken C2/C5/C7/C8/C9/C10/C12 or capture ownership |

---

## State Transitions (conceptual)

### Evidence sufficiency

```text
unknown → complete | partial | missing   (Evidence assessment)
partial|complete → partial|missing       (Context budget omission may degrade)
```

Degradation via budget MUST be recorded; sufficiency MUST NOT silently upgrade downstream.

### No-answer decision

```text
signals (sufficiency, conflicts, ambiguity, domain, policy)
    → NoAnswerDecision.condition
    → AnswerResult (answer | limited | no-answer)
```

### Claim grounding

```text
Answer Draft → Claim Extraction → Evidence Verification
    → grounded | ungrounded | limited
    → Citation Resolution (grounded only)
    → Final Answer
```

---

## Relationships to 016 Ownership

| Entity cluster | Owner concern_id |
|----------------|------------------|
| UnderstoodQuery | `query_understanding` |
| RetrievalPlan / Strategy* | `retrieval_planning` |
| CandidateLifecycle / CalibratedScoreSet | `retrieval_execution` |
| EvidencePack / Coverage / ConflictCandidate | `evidence_organization` |
| Context / CitationMap / ConflictGroup | `context_assembly` |
| AnswerResult / ClaimGrounding / NoAnswer | `answer_generation` |
| Offline metric authority | `offline_evaluation_orchestration` / scoring (014) |
| Extension wiring | `composition_wiring` |

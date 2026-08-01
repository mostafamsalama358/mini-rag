# Contract: Evidence & Context Quality

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative contracts for Evidence quality model, coverage/missing-evidence, Context priority, and compression.

---

## Purpose

Maximize evidence quality and token-efficient, citation-safe context without absorbing Answer Generation responsibilities.

---

## A. Evidence Quality Model (Evidence-owned)

Evidence items carry diagnostic dimensions beyond relevance:

- Authority
- Freshness
- Completeness
- Semantic coverage
- Locality
- Confidence

### Rules

1. Dimensions are diagnostic; absence MUST be `unknown`, not implicit excellence.
2. Ordering MAY use these with calibrated relevance; MUST remain stable/explainable.
3. Evidence MUST NOT trigger answer generation.

---

## B. Coverage Validation & Missing Evidence (Evidence-owned)

### Sufficiency states

`complete` | `partial` | `missing`

### Rules

1. Evidence Orchestrator MUST emit CoverageAssessment + sufficiency into Evidence Pack metadata and Quality Context.
2. Coverage validation MUST remain separate from Answer Generation ownership (C10).
3. Context MAY record budget-driven coverage degradation; MUST NOT invent upstream completeness.
4. Answer Generation consumes signals for no-answer/limited-answer; MUST NOT become a competing coverage authority.
5. Feature 014 remains offline golden coverage scoring authority.

---

## C. Deduplication Ladder (shared continuity)

1. Engine — identity dedup  
2. Evidence — content exact/near-duplicate collapse  
3. Context — final safety-net under budget  

Later layers MUST NOT destroy citation attribution (C3).

---

## D. Context Priority Model (Context-owned)

Selection preference under token budget (high → low):

1. Conflict evidence  
2. Primary evidence  
3. Supporting evidence  
4. Contextual evidence  
5. Background evidence  
6. Redundant evidence  

### Rules

1. Lower classes are compressed/dropped before higher classes.
2. Conflict evidence MUST NOT be reduced to one side without `resolution: omission` (C4).
3. Structural document/section ordering applies **after** priority-preserving selection.
4. Context MUST NOT re-retrieve.

---

## E. Context Compression Policy (Context-owned)

| Class | Rule |
|-------|------|
| Compressible | Background, redundant, and eligible supporting/contextual items |
| Non-compressible | Conflict-critical and primary grounding anchors that would lose meaning |

### Preservation (retained blocks)

- Citation continuity (C5)
- Conflict distinguishability (C4)
- Grounding anchors for claim support (C12)

Failed compression → include-or-drop with trace; no fabricated filler (C6/C7).

---

## Acceptance

Designs that hide partial/missing evidence, treat scores as completeness, or compress away conflict/primary anchors without trace fail review.

---

## Non-Goals

- Compression algorithms or similarity thresholds
- Concrete tokenizers
- Domain-specific facet taxonomies (belong in Domain Packs via extension points)

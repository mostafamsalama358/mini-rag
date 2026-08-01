# Contract: Compatibility with Features 014–017

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative compatibility rules so quality architecture cannot violate existing Spec Kit features.

---

## Purpose

Preserve evaluation authority, cutover vehicle, sole-owner governance, and ingest orthogonality.

---

## Feature 014 — Answer Quality

| Rule | Requirement |
|------|-------------|
| Offline authority | 014 remains the offline golden/regression authority for coverage, faithfulness, completeness |
| No metric redefinition | 018 stage metrics are diagnostic; they do not replace 014 definitions |
| Feedback | 014 may feed configuration improvements; evaluation stays offline |
| Disagreement | 014 wins for release/cutover quality decisions |

---

## Feature 015 — Unified Pipeline Migration

| Rule | Requirement |
|------|-------------|
| Dual-run | Transitional only; not a permanent second quality/answer path |
| Frozen external answer API | 018 MUST NOT require redesign of frozen external answer fields |
| Internal richness | Quality Context/Trace MAY exceed external exposure |

---

## Feature 016 — Architecture Consolidation

| Rule | Requirement |
|------|-------------|
| Sole owner | Exactly one production owner per concern; 018 extends contracts, does not reassign owners |
| M0 freeze | No new parallel production implementations for the same concern without superseding governance ADR |
| Composition | Remains sole wiring authority for extensions |
| Domain Packs | Extend via published points; must not capture core orchestration |

---

## Feature 017 — Scalability & Reliability

| Rule | Requirement |
|------|-------------|
| Orthogonality | 017 hardens sole ingest path; 018 does not redesign ingest/publish lifecycle |
| Shared observability | Correlation/observability vocabulary may align; ownership stays capability-specific |
| No coupling | Quality contracts MUST NOT depend on ingest job control-plane entities |

---

## Acceptance

Architecture review fails if 018 design:

1. Introduces a permanent second retrieval or answer path  
2. Moves evaluation onto the request path as an owner  
3. Reassigns 016 ownership without superseding governance  
4. Redefines 014 golden metrics  
5. Couples answer-quality contracts to 017 ingest job lifecycle  

---

## Non-Goals

- Replacing 015/016/017 plans
- Authoring exception ADRs in this feature (out of 018 plan scope)

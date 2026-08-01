# Research: Pharmacy Recommendation Capability

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

Phase 0 decisions resolving planning unknowns. Aligns with [spec.md](./spec.md) and [ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md). No implementation code prescriptions.

---

## R1 — Capability vs Service / API / parallel path

**Decision**: Recommendation is a **Domain Pack capability** on the sole Answer + Retrieval path. No Recommendation Service, no Recommendation API, no parallel production pipeline, no new sole owner.

**Rationale**: 016 M0 freeze and frozen `/answer` (015) forbid dual production paths and breaking public contracts. Spec Non-goals and ADR-020-001 bind this.

**Alternatives considered**:
- Dedicated Recommendation Service + API — rejected (new owner, M0 violation, API expansion)
- Shadow dual recommend pipeline — rejected (015/016 dual-path risk)
- Capability composition (**selected**)

---

## R2 — Where Need Frame and recommend intent live

**Decision**: Recommend / suggest-therapy / need-based intent and **Need Frame** population are **Query Understanding** concerns (pharmacy `parser` pack + core query parser). Fields are optional per query.

**Rationale**: Spec FR-001/FR-002; 004/018 handoff already owns understood-query shape. Avoids a pre-retrieval “recommend microservice.”

**Alternatives considered**:
- Answer-stage-only intent guess — rejected (too late for retrieval constraints)
- Separate intent service — rejected (ownership creep)

---

## R3 — Symptom Taxonomy vs flat dictionary

**Decision**: Matching uses a **controlled Symptom Taxonomy** (many-to-many, hierarchy, synonyms, AR/EN normalization, versioned pack artifact)—not a one-off phrase dict.

**Rationale**: Spec §Symptom Taxonomy; supports clarification, eval stability, and expansion without code forks.

**Alternatives considered**:
- Flat synonym dict only — rejected (no hierarchy/ambiguity model)
- Free-form LLM tagging without vocabulary — rejected (non-reviewable, weak eval)

---

## R4 — Candidate generation on sole retrieval path

**Decision**: Candidate sets come from **metadata constraints + hybrid retrieval + fusion + rerank** on the existing retrieval engine/planner path. Indication tags and identity metadata are first-class filters/constraints.

**Rationale**: Spec logical flow; constitution hybrid+rerank; 010/009 ownership unchanged.

**Alternatives considered**:
- Catalog-only SQL recommend bypassing hybrid — rejected as sole path (loses evidence/rerank; risk of parallel path)
- Open-web drug lists — rejected (corpus-boundedness)

---

## R5 — Recommendation Ranking Model

**Decision**: **Recommendation Score** = policy-composed signals: Indication Match, Retrieval Evidence, Reranker Confidence, Safety Fitness, optional Formulary/Preference. **No fixed weights in architecture artifacts**; Recommendation Policy owns weights/enablement/tie-breaks.

**Rationale**: Spec Ranking Model; reviewable & explainable; avoids baking unvalidated numbers into plan/contracts.

**Alternatives considered**:
- Single opaque model score — rejected (fails explainability)
- Hardcoded weights in spec/plan — rejected (premature; policy-owned)

---

## R6 — Safety Model extensibility

**Decision**: Safety Label is an **extensible dimension catalog** (pregnancy, breastfeeding, pediatric, elderly, renal/hepatic, diabetes, hypertension, contraindications, interaction severity, OTC/Rx, …). **v1 MAY implement a subset** (expected start: pregnancy + breastfeeding). Unknown ≠ safe.

**Rationale**: Spec Safety Model; prevents two-field dead-end while allowing incremental ingest coverage.

**Alternatives considered**:
- Pregnancy/breastfeeding only forever — rejected (forced redesign later)
- Require all dimensions in v1 — rejected (blocks delivery; data incomplete)

---

## R7 — Product Identity Rules

**Decision**: Identity hierarchy **Brand → Product Line → Strength → Package** guides ranking slots and presentation. Distinct lines/strengths are not false duplicates; package-only variants should not consume multiple recommendation slots when irrelevant to the need.

**Rationale**: Spec Product Identity Rules; pharmacy corpus has multi-SKU families (e.g. Panadol lines).

**Alternatives considered**:
- Always rank every SKU independently — rejected (redundant lists)
- Always collapse to brand — rejected (loses migraine vs cold line distinctions)

---

## R8 — Explanation vs operator explainability

**Decision**: **User-facing** answers follow Explanation Policy (evidence-only; no hidden scores; no unsupported clinical superiority; recommendation ≠ medical advice). **Operators** get Matched Indications, Retrieved Evidence, Safety Outcome, Rank Contribution via Recommendation Trace / Quality Context (018)—not a new public API.

**Rationale**: Spec FR-019 + Candidate Explainability; preserves 015 wire contract.

**Alternatives considered**:
- Expose raw scores in `/answer` — rejected (contract/PII/UX; not frozen fields)
- No operator trace — rejected (018/019 defect attribution fails)

---

## R9 — Evaluation ownership

**Decision**: 020 defines the **recommend metric catalog** (Recall@K, Precision@K, MRR, nDCG, Safety Precision/Recall, False Recommendation Rate, Clarification Rate, Corpus-Boundedness, Recommendation Diversity). **Feature 019 implements** profiles, judges, gates, runners, and thresholds-as-ops-policy.

**Rationale**: Spec Evaluation Metrics; 019 is evaluation architecture authority; avoids parallel eval owner.

**Alternatives considered**:
- Embed runners inside 020 production path — rejected (018/019 non-ownership of request-path eval)
- Skip metrics until “later” — rejected (SC-008 / ship gates)

---

## R10 — Ingest / metadata dependency

**Decision**: Indication tags, Safety Labels, and product-identity fields MUST be **ingestible and indexed** (006/017 sole ingest path). Leaflets remain narrative evidence during transition; structured workbook fields feed labels iteratively. Recommend-mode MUST NOT rely on prompt memorization of the catalog.

**Rationale**: Spec FR-015; corpus-bounded grounded recommendations.

**Alternatives considered**:
- Prompt-only drug memory — rejected (hallucination / out-of-corpus risk)
- Second ingest pipeline for recommend — rejected (017/016)

---

## R11 — API and clarification signals

**Decision**: Clarification and limited coverage use **existing** answer signals (`needs_clarification`, clarification `signal` values) and answer text. No new recommend-specific response fields in the frozen external contract.

**Rationale**: 015 api-stability; FR-011.

**Alternatives considered**:
- New `recommendations[]` wire field — deferred/rejected for v1 without separate versioned API change
- Side-channel recommend endpoint — rejected (ADR-020-001)

---

## R12 — Performance posture

**Decision**: Prefer **no extra mandatory LLM hop** beyond existing parse + compose. Taxonomy mapping SHOULD be deterministic/pack-driven where possible; LLM parse may emit Need Frame fields already in the understanding step.

**Rationale**: Keep answer-path latency envelope; Celery reserved for ingest/tag curation, not per-recommend scoring.

**Alternatives considered**:
- Extra “recommend planner” LLM call every request — rejected as default (latency/cost); optional only with explicit task-level budget approval

---

## Resolved clarifications

| Topic | Resolution |
|-------|------------|
| New service/API? | No (R1) |
| Fixed ranking weights? | No — Policy-owned (R5) |
| Full safety dimensions in v1? | Optional subset (R6) |
| Eval implementation owner? | 019 (R9) |
| Wire contract change? | None for v1 (R11) |

**Unresolved NEEDS CLARIFICATION**: none.

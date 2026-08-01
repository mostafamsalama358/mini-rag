# Research: RAG Quality Architecture

**Feature**: 018-rag-quality-architecture | **Date**: 2026-07-18

Phase 0 decisions resolving architectural unknowns for the quality design. No implementation prescriptions.

---

## R1 — Query Understanding vs Planner authority

**Decision**: Understood Query is the sole intent authority for planning. Planner consumes parse quality signals and MUST NOT re-parse raw user text as a competing authority.

**Rationale**: Dual parse authorities cause strategy drift and unattributable quality failures. Feature 016 already separates `query_understanding` from `retrieval_planning`.

**Alternatives considered**:
- Planner re-parses for “robustness” — rejected (breaks C9, duplicates ownership)
- Application merges raw text + plan ad hoc — rejected (non-contractual)

---

## R2 — Strategy architecture location

**Decision**: Strategy Registry, Capability Model, Selection/Ordering/Degradation/Compatibility policies live under Retrieval Planner ownership. Engine executes ordered strategies; may only degrade with trace, not re-select strategy families silently.

**Rationale**: Spec requires explainable selection without retrieval execution. Aligns with 009 “what vs how” boundary and 016 retrieval_planning vs retrieval_execution split.

**Alternatives considered**:
- Engine-owned strategy selection — rejected (re-planning in execution)
- Domain Packs as registry owners — rejected (packs contribute hints only)

---

## R3 — Candidate lifecycle & score calibration ownership

**Decision**: Full candidate lifecycle including score calibration is owned by Canonical Retrieval Owner (Engine). Calibration normalizes heterogeneous signals before Candidate Selection; no mathematics specified here.

**Rationale**: Scores originate in retrieval legs/rerank; calibrating elsewhere creates a second ranking authority. Evidence ordering may *use* calibrated scores but must not recalibrate as a competing owner.

**Alternatives considered**:
- Evidence-owned calibration — rejected (duplicates Engine ranking authority)
- Answer-owned score reinterpretation — rejected (too late; breaks attribution)

---

## R4 — Coverage validation & missing evidence

**Decision**: Coverage assessment and complete/partial/missing states are owned by Evidence Orchestrator. Answer Generation consumes signals for no-answer/limited-answer. Feature 014 remains offline golden coverage authority.

**Rationale**: Spec requires coverage separate from answer generation. Placing it in Answer would incent generative “completion” of gaps. Placing it only offline would hide runtime honesty.

**Alternatives considered**:
- Context-owned coverage — rejected as primary (Context may record budget impact only)
- Answer-owned coverage — rejected (C10)
- Runtime 014 evaluator — rejected (eval must stay offline; §18 / 016)

---

## R5 — Context priority vs structural ordering

**Decision**: Priority classes (conflict → primary → supporting → contextual → background → redundant) govern *selection under budget*. Structural document/section ordering applies *after* priority-preserving selection.

**Rationale**: Structural order improves readability but must not drop conflict/primary evidence in favor of coherent but low-value sections.

**Alternatives considered**:
- Relevance-only selection — rejected (ignores conflict retention)
- Structure-first selection — rejected (risks dropping primary/conflict under budget)

---

## R6 — Compression vs non-compressible evidence

**Decision**: Architecture distinguishes compressible vs non-compressible classes. Conflict-critical and primary grounding anchors resist compression that would destroy meaning; citation/conflict/grounding preservation is mandatory for retained blocks.

**Rationale**: Blind compression is a common citation and conflict failure mode. Spec forbids fabricating filler when compression fails.

**Alternatives considered**:
- Compress everything equally — rejected (breaks C4/C5/C12)
- Never compress — rejected (token efficiency / C6)

---

## R7 — Citation chain shape

**Decision**: Normative logical chain is Evidence → Chunk → Document → Source → Citation. Continuity must survive compression and budgeting for included blocks.

**Rationale**: Matches existing staged attribution concepts (011–013) while making end-to-end continuity explicit for quality review.

**Alternatives considered**:
- Citation as free-text only — rejected (non-auditable)
- Answer invents document titles without chain — rejected (hallucination vector)

---

## R8 — Conflict category taxonomy

**Decision**: Categories are semantic, temporal, authority, version, duplicate disagreement. Ownership split unchanged: Evidence (candidates/categories) → Context (disclosure-ready + budget omission) → Answer (user disclosure).

**Rationale**: Categories improve diagnosis without creating a Conflict Owner. Duplicate disagreement bridges dedup ladder and conflict continuity.

**Alternatives considered**:
- Single undifferentiated “conflict” bit — rejected (weak diagnostics)
- New Conflict Orchestrator stage — rejected (C8 / sole-owner)

---

## R9 — Answer verification as logical sub-pipeline

**Decision**: Draft → Claim Extraction → Evidence Verification → Citation Resolution → Final Answer are logical responsibilities **inside** Answer Generation ownership — not a separate production path or owner.

**Rationale**: Claim-level grounding requires structured verification, but a second pipeline would violate 016 M0/C8 and freeze dual-path Answer (015 transitional only).

**Alternatives considered**:
- Separate Verification service owner — rejected (sixth owner / parallel path risk)
- Whole-answer-only grounding — rejected (spec §13; unsupported claims slip through)

---

## R10 — No-answer condition model

**Decision**: Answer Generation decides among architectural conditions (no/weak/conflicting/partial evidence, ambiguous, out-of-domain, restricted) using upstream signals. Upstream stages own signal honesty, not the final user posture alone.

**Rationale**: Prevents “always answer” pressure from overriding empty/partial/ambiguous reality.

**Alternatives considered**:
- Binary empty-context-only no-answer — rejected (misses weak/partial/conflict/ambiguity)
- Planner-owned user-facing no-answer — rejected (wrong layer; Answer owns result)

---

## R11 — Quality Context vs Quality Trace

**Decision**: Quality Context = cumulative current quality state enrichable by every stage (additive / namespaced). Quality Trace = append-only sectioned diagnostics (Plan, Retrieval, Expansion, Fusion, Rerank, Evidence, Context, Generation, Verification). Neither replaces stage outputs.

**Rationale**: Operators need both “where are we now” and “what happened in each section” for attribution and 014 offline analysis.

**Alternatives considered**:
- Trace-only — rejected (harder for downstream decision inputs)
- Mutating shared bag that overwrites upstream — rejected (ownership violation)
- User-facing API exposure of full trace — deferred/non-required (015 freeze)

---

## R12 — Offline feedback loop

**Decision**: Feature 014 evaluates offline; feedback may update configuration, Domain Pack profiles, and strategy registry hints via Composition. Evaluation never becomes request-path owner. On disagreement, 014 wins for release/cutover.

**Rationale**: Matches 016 offline_evaluation ownership and spec §18. Prevents latency/ownership collapse from inline judges.

**Alternatives considered**:
- Inline faithfulness judge as production gate owner — rejected
- Redefining 014 metrics inside 018 — rejected (Out of Scope)

---

## R13 — Extension model

**Decision**: Each stage has explicit extension points; Domain Packs and provider adapters extend; Composition wires. Extensions may tighten quality, not weaken C2/C5/C7/C8/C9/C10/C12.

**Rationale**: Preserves 016 P8/P12 (packs extend without capturing core) and constitution pluggable providers.

**Alternatives considered**:
- Open mutation of core contracts by packs — rejected
- No extensions (hardcode domains) — rejected (constitution / 002)

---

## R14 — Relationship to 015 / 017

**Decision**: 015 dual-run remains transitional cutover vehicle only. 017 ingest reliability is orthogonal; 018 does not redesign ingest or publishing.

**Rationale**: Spec compatibility table; avoids scope collision with active 017 hardening.

**Alternatives considered**:
- Permanent dual answer path “for quality A/B” — rejected (C8)
- Tie quality contracts to ingest job lifecycle — rejected (wrong capability)

---

## Resolved NEEDS CLARIFICATION

None remain. All Technical Context items for this architecture plan are resolved as documentation-scope constraints (no stack change, no latency program, no layout winners).

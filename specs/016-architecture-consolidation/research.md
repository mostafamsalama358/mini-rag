# Research: Architecture Consolidation

**Feature**: 016-architecture-consolidation | **Date**: 2026-07-18

Phase 0 resolves planning unknowns for a governance-first consolidation plan. Decisions favor long-term maintainability over short-term layout coupling.

---

## R-001: Plan artifact style — governance vs implementation blueprint

**Decision**: Keep plan/research/contracts at architecture-governance level; forbid package winners and coding steps in 016 artifacts.

**Rationale**: Spec P9/P13/P14 and Out of Scope ban implementation planning. A layout-bound plan would immediately drift when folders rename and would violate Owner Selection Criteria.

**Alternatives considered**:
- (A) Name surviving modules now — rejected (AP12/AP14).
- (B) Governance + migration outcomes only — chosen.
- (C) Hybrid “suggested packages” appendix — rejected; becomes de facto normative.

---

## R-002: Relationship to 015 unified pipeline migration

**Decision**: Treat 015 as the assumed answer cutover vehicle (dual-run → sole path). 016 owns target governance, ownership, lifecycle, and post-cutover retirement meaning.

**Rationale**: Spec Assumptions and ADR-001/002. Redesigning cutover inside 016 duplicates product scope and smuggles implementation planning.

**Alternatives considered**:
- (A) Ignore 015 and redefine cutover — rejected (scope creep).
- (B) Merge 015 into 016 — rejected (different artifact maturity/purpose).
- (C) 015 = mechanism, 016 = governance target — chosen.

---

## R-003: How to represent “canonical contracts” without concrete types

**Decision**: Contracts are named by **concept role** (understood query, retrieval results, evidence set, assembled context, generated answer, external answer response, parsed document, chunk/indexable units). Identity is uniqueness + consumer compatibility, not type/file names.

**Rationale**: Spec ADR pattern “contracts over concrete types” absorbed into Principles; physical type consolidation is a later implementation concern under Owner authority.

**Alternatives considered**:
- (A) Normative list of today’s class names — rejected (couples plan to code).
- (B) Concept-role contracts — chosen.
- (C) Omit contracts entirely — rejected (P3/I3 require them).

---

## R-004: Owner selection process when candidates compete

**Decision**: Apply Owner Selection Criteria scoring; require architecture review sign-off; issue ADR only when alternatives were genuinely valid and contested.

**Rationale**: Spec Owner Selection Criteria + ADR admission rule. Prevents age/folder politics (AP12).

**Alternatives considered**:
- (A) Always pick “newer stack” — rejected.
- (B) Always keep “currently wired” — rejected without criteria.
- (C) Criteria-based selection with optional ADR — chosen.

---

## R-005: Enforcement mechanism for governance (review vs automation)

**Decision**: Phase-0/1 normative enforcement is **architecture review + validation checklist** (quickstart). Optional later automation (import linters, path-selection assertions) is allowed but not designed here.

**Rationale**: Designing lint rules now would become coding guidance and may false-positive during legitimate transition phases.

**Alternatives considered**:
- (A) Mandate CI import linter in this plan — deferred (implementation).
- (B) Review/gates only for 016 planning — chosen.
- (C) No enforcement — rejected (governance theater).

---

## R-006: Search interim ownership documentation

**Decision**: Until Search shares Answer’s retrieval Owner, interim ownership MUST be explicitly recorded in implementation docs / ops notes; absence = Hidden Production Path (AP10/I13).

**Rationale**: ADR-002 allows temporary divergence only if documented.

**Alternatives considered**:
- (A) Force Search cutover in same phase as Answer — rejected (blast radius).
- (B) Allow silent divergence — rejected (I13).
- (C) Explicit interim owner — chosen.

---

## R-007: Knowledge capability lifecycle default

**Decision**: Default lifecycle = Activation Pending Consumer (or Research Capability if no consumer is planned). Activation requires a declared consumer + Owner Selection + governance updates.

**Rationale**: ADR-004. Prevents false “production complete” claims without forcing premature wiring or deletion.

**Alternatives considered**:
- (A) Wire immediately — rejected (blocks consolidation, Out of Scope feature work).
- (B) Delete now — may be valid later under Owner decision; not mandated by 016.
- (C) Lifecycle honesty — chosen.

---

## R-008: Where detailed ownership inventory lives

**Decision**: Detailed Owner→module inventories live in implementation documentation (e.g. architecture guide updates), not in 016 spec/plan body.

**Rationale**: P13 — architecture specs define rules; catalogs drift.

**Alternatives considered**:
- (A) Full inventory in spec — rejected (became unmaintainable in prior draft).
- (B) Rules + examples in 016; inventory elsewhere — chosen.

---

## R-009: Validation reuse of offline answer quality

**Decision**: Reuse existing offline evaluation capability as Answer M1 quality gate; do not redesign scorers or golden methodology in 016.

**Rationale**: Spec D5 / Out of Scope (model evaluation changes). 014 remains the gate mechanism if present; thresholds may live in ops runbooks.

**Alternatives considered**:
- (A) New evaluation framework in 016 — rejected (Out of Scope).
- (B) No quality gate — rejected (unsafe cutover).
- (C) Reuse existing gate — chosen.

---

## R-010: Re-index policy when chunk/embed-text policy unifies

**Decision**: Treat material embed-text/chunk policy unification as a compatibility event requiring re-index or an explicit recorded waiver with risk acceptance (spec D7).

**Rationale**: Silent corpus skew is a known consolidation hazard.

**Alternatives considered**:
- (A) Always mandate immediate re-index in plan — too operationally rigid for all environments.
- (B) Ignore — rejected.
- (C) Re-index or documented waiver — chosen.

---

## R-011: ADR admission filter

**Decision**: Keep only ADR-001..004 in 016. Standing rules stay Principles/Invariants/Anti-Patterns.

**Rationale**: Spec iteration feedback — ADRs must be real tradeoffs. Prevents ADR inflation that dilutes decision history.

**Alternatives considered**:
- (A) ADR per principle — rejected.
- (B) Strict tradeoff filter — chosen.

---

## R-012: Orchestration independence

**Decision**: Capability architecture enumerates required concerns and contract dependencies; does not mandate a single global stage sequence diagram as identity of the system.

**Rationale**: Spec P14. Prevents freezing today’s orchestration as “architecture.”

**Alternatives considered**:
- (A) Fixed Parse→…→Answer sequence as invariant — rejected as over-prescription.
- (B) Concerns + contract dependencies — chosen.
- (C) Free-form anything — rejected (still need required concerns).

---

## Resolved Clarifications

No open `NEEDS CLARIFICATION` items remain in Technical Context. Operational numeric soak thresholds are explicitly deferred to runbooks (spec Assumptions) without blocking architecture decisions.

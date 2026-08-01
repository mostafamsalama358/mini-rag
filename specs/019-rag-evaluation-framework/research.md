# Research: RAG Evaluation Framework

**Feature**: 019-rag-evaluation-framework | **Date**: 2026-07-18

Phase 0 decisions resolving architectural unknowns for the evaluation design. No implementation prescriptions.

---

## R1 — Evaluation architecture authority vs Feature 014

**Decision**: Feature **019** is the evaluation architecture authority (modes, profiles, ownership, governance, monitoring). Feature **014** remains the semantic seed for coverage, Faithfulness, and Completeness; those definitions are preserved, not redefined.

**Rationale**: 014 covers a necessary but incomplete offline golden slice. Production RAG needs retrieval IR metrics, planner evaluation, citation/hallucination rates, latency/cost, online drift, and governance — without discarding proven 014 semantics.

**Alternatives considered**:
- Keep 014 as sole evaluation authority — rejected (cannot express full framework)
- Redefine Faithfulness/Completeness under new names — rejected (breaks continuity with 014/018 feedback loop)

---

## R2 — Evaluation must not be a production stage

**Decision**: Evaluation runs offline, in CI, on shadow/canary observation paths, or as asynchronous monitoring. It MUST NOT own user-facing answer generation or create a parallel retrieval/answer path.

**Rationale**: Feature 016 sole-owner and M0 freeze forbid dual production paths. 018 already forbids request-path evaluation ownership.

**Alternatives considered**:
- Inline mandatory evaluation on every answer — rejected (latency, ownership collision, 018 §18)
- Shadow path as second production owner — rejected (015/016)

---

## R3 — Exactly one primary owner per failed metric

**Decision**: Metric Ownership assigns exactly one Primary Owner per canonical metric for regression attribution. Supporting Stages are diagnostic only. Latency/Cost use “Whole Pipeline (operational attribution)” as an evaluation attribution sink — not a new 016 production owner.

**Rationale**: Multi-owner blame makes gates non-actionable. Dependency model annotates root cause without reassigning Primary Owner.

**Alternatives considered**:
- Split ownership percentages — rejected (ambiguous gates)
- Always blame Answer Generation for downstream symptoms — rejected (hides retrieval/planner defects)

---

## R4 — Metric dependency vs ownership

**Decision**: Dependency model orders upstream→downstream effects (Planner → Retrieval → Evidence → Context → Faithfulness → Groundedness → Completeness → Citation/Hallucination). Root-cause annotation is additive; Primary Owner rows remain authoritative for each metric.

**Rationale**: Spec requires both per-metric ownership and causal interpretation when multiple metrics fail.

**Alternatives considered**:
- Dependency reassigns owner automatically — rejected (unstable attribution)
- No dependency model — rejected (completeness failures look like pure generation bugs)

---

## R5 — Evaluation Profiles over ad hoc suites

**Decision**: Reusable profiles (Smoke, PR, Nightly, Weekly, Release, Shadow, Production Monitoring) bind dataset tiers, enabled metric sets, gate type, and runtime/cost expectation *classes* — without concrete numeric thresholds in architecture.

**Rationale**: Different assurance levels need different cost/runtime envelopes; thresholds are planning/ops policy, not architecture identity.

**Alternatives considered**:
- Single always-on full suite — rejected (too heavy for PR)
- Encode thresholds in architecture — rejected (violates architecture-only constraint)

---

## R6 — Judge Layer interchangeability

**Decision**: Abstract Judge Layer supports Rule, LLM, Human, and Hybrid judges. Metric identities and semantics stay stable across judge implementations. Runs record judge type/version; optional confidence/agreement/provenance support multi-judge futures.

**Rationale**: Spec requires future multi-judge systems without contract churn; implementations remain out of scope.

**Alternatives considered**:
- Rule-only forever — rejected (insufficient for nuanced groundedness at scale)
- LLM-judge defines new metrics — rejected (metric instability)

---

## R7 — Dataset and benchmark governance

**Decision**: Datasets and benchmarks share lifecycle concepts (Draft → Approved → Frozen → Retired/Superseded) with approval, freeze immutability, lineage, changelog, compatibility, and reproducibility guarantees. Blocking profiles require frozen pins.

**Rationale**: Release claims are meaningless without immutable subjects and version lineage.

**Alternatives considered**:
- Mutable golden files in place — rejected (non-reproducible)
- Benchmarks as ungoverned scrapes — rejected (incomparable releases)

---

## R8 — Offline gates vs online drift

**Decision**: Offline profile gates remain primary merge/release authority. Drift Taxonomy (Data/Query/Retrieval/Ranking/Citation/Answer/Latency/Cost) explains live divergence; alerts notify; gates decide. Persistent drift feeds Dataset Evolution, not silent threshold relaxation.

**Rationale**: Spec separates Online Drift Gate / Ops Gate from PR Core authority while still operationalizing production monitoring.

**Alternatives considered**:
- Online metrics block every merge — rejected (label sparsity, noise)
- Monitoring without taxonomy — rejected (unactionable “quality dropped” alerts)

---

## R9 — Experiment roles without deployment mechanics

**Decision**: Architectural roles Baseline, Candidate, Champion, Challenger, Shadow, Canary describe evaluation comparison posture. Traffic shifting, rollout percentages, and infra are out of scope.

**Rationale**: Needed for champion/challenger reporting and 015-compatible shadow observation without turning 019 into a delivery/platform feature.

**Alternatives considered**:
- Encode canary deployment steps — rejected (out of scope / implementation)
- Diff runs only by timestamp — rejected (loses experiment semantics)

---

## R10 — Composite scores as derived views

**Decision**: Overall / Retrieval / Planning / Generation / Production Health composites are derived reporting indicators with mandatory drill-down. They do not replace per-metric blocking gates unless a profile explicitly names a composite as advisory (default) or rare named gate input.

**Rationale**: Executives need rollups; engineers need owners and taxonomies.

**Alternatives considered**:
- Single Overall score as only gate — rejected (hides safety regressions)
- No composites — rejected (weak executive/ops communication)

---

## R11 — Error Taxonomy separate from production stages

**Decision**: Eight evaluation error categories (Retrieval, Planner, Context, Citation, Grounding, Generation, Evaluation, Infrastructure) standardize reporting. Evaluation/Infrastructure failures must not become silent PASS under blocking profiles.

**Rationale**: Aligns dashboards and attribution without creating new 016 owners.

**Alternatives considered**:
- Reuse only stage names — rejected (cannot express eval/infra failures cleanly)
- Free-text error reasons only — rejected (non-aggregable)

---

## R12 — Relationship to 018 Quality Trace

**Decision**: Prefer Quality Context / Quality Trace (018) as telemetry enrichment for monitoring and offline alignment. Do not invent a second competing telemetry model; Evaluation Run Metadata is the evaluation-specific reproducibility record.

**Rationale**: Continuity with 018; avoids duplicate observability ownership.

**Alternatives considered**:
- Parallel eval-only telemetry ontology — rejected (duplication, drift from production traces)

---

## R13 — Future extension points

**Decision**: Multimodal, Agent, Conversation, Tool Calling, Long Context, Multi-hop, Safety, and Reasoning evaluation are listed as future-compatible extension points only. They reuse profiles/judges/ownership patterns and do not expand current scope or production owners.

**Rationale**: Spec §Future Evaluation Extensions; prevents premature scope expansion in plan phase.

**Alternatives considered**:
- Specify full agent/conversation metrics now — rejected (scope change)

---

## Resolved NEEDS CLARIFICATION

None remain. Technical Context unknowns were resolved by architecture defaults above and Assumptions in [spec.md](./spec.md).
)

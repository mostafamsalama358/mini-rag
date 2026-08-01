# Feature Specification: RAG Quality Architecture

**Feature Branch**: `018-rag-quality-architecture`

**Created**: 2026-07-18

**Updated**: 2026-07-18

**Status**: Draft

**Input**: Design improvements for retrieval quality and answer quality across Retrieval Planner, Retrieval Engine, Evidence Orchestrator, Context Builder, and Answer Generation — refined to close architectural gaps in query-understanding handoff, strategy architecture, candidate lifecycle, score calibration, evidence quality, coverage and missing-evidence signals, context priority/compression, citation and conflict models, answer verification, claim-level grounding, hallucination prevention, no-answer decisions, quality trace/context, stage metrics, offline feedback, and extension points. Architecture refinement only.

**Artifact type**: Architecture specification for maximizing retrieval quality, evidence quality, grounding quality, and final answer quality. Implementation, algorithms, code, pseudocode, class diagrams, task breakdown, ADRs, and sprint planning are out of scope.

---

## Scope

### In Scope

- Quality contracts and stage obligations across Query Understanding → Planner → Engine → Evidence → Context → Answer Generation (including logical verification responsibilities inside Answer Generation)
- Cross-stage continuity: Quality Context, Quality Trace, citation chain, conflict model, hallucination prevention chain, no-answer decision model
- Strategy architecture (registry, capability model, selection/ordering/degradation/compatibility) without retrieval execution
- Retrieval candidate lifecycle with clear ownership per responsibility
- Evidence quality model, coverage validation, and missing-evidence distinction as diagnostic architectural signals
- Context priority and compression policies at architecture level
- Claim-level grounding and answer verification as logical responsibilities of the Answer Generation owner
- Stage quality metrics and offline feedback loop from feature 014 — without runtime ownership change
- Extension points per stage that preserve contracts and sole ownership
- Compatibility with features 014, 015, 016, and 017

### Out of Scope

- Implementation code, algorithms, mathematical formulas, provider selection, or model choice
- Pseudocode, class diagrams, file/package layout, or sprint/task breakdown
- Architecture Decision Records and implementation planning
- New parallel production owners or dual execution paths for retrieval or answer
- Redesign of ingest, chunking, or document parsing pipelines (feature 017 remains orthogonal)
- Redesign of the frozen external answer API field-level contract (feature 015)
- Replacement or redefinition of offline golden/evaluation metrics (feature 014 remains evaluation authority)
- Merging of stages or creation of a sixth production “quality” owner
- Domain-specific vertical rules that belong in Domain Packs rather than core stage owners

---

## Relationship to Existing Features

| Feature | Relationship |
|---------|--------------|
| 004 Semantic Query Parser | Query Understanding library; supplies Understood Query contract consumed by Planner |
| 009 Retrieval Planner | Stage library being quality-hardened; planning ownership unchanged (016) |
| 010 Retrieval Engine | Stage library being quality-hardened; execution ownership unchanged (016) |
| 011 Evidence Orchestrator | Stage library being quality-hardened; evidence ownership unchanged (016) |
| 012 Context Builder | Stage library being quality-hardened; context ownership unchanged (016) |
| 013 Answer Generation | Stage library being quality-hardened; generation ownership unchanged (016); verification is logical sub-responsibility of this owner |
| 014 Answer Quality | Offline evaluation authority and feedback source; not redesigned; metrics not redefined |
| 015 Unified Pipeline Migration | Dual-run / cutover vehicle for Answer; this spec does not introduce a second answer path |
| 016 Architecture Consolidation | Governance baseline; sole-owner and M0 freeze are binding |
| 017 Scalability & Reliability | Orthogonal ingest reliability; this spec is answer/retrieval quality architecture only |

This specification **extends quality contracts**. It does **not** reassign ownership. Where a quality improvement would require a second owner for an existing concern, it is rejected in favor of extending the canonical owner’s contract.

---

## Design Principles (Preserved)

1. **Clean Architecture & dependency direction** — Presentation → Application → Core contracts → Infrastructure providers
2. **Contract-first** — Stages exchange stable contracts; quality metadata accumulates without replacing stage outputs
3. **Single responsibility & modularity** — Stages are not merged; safety-net layers do not create dual owners
4. **Sole-owner (016)** — Exactly one production owner per concern; no parallel retrieval or answer pipelines
5. **Deterministic stage boundaries** — Identical inputs and configuration yield attributable, reviewable stage outputs
6. **Quality as continuity** — Retrieval, evidence, grounding, and answer quality improve through handoff contracts, not through a side pipeline

---

## Canonical Quality Pipeline

Logical flow (stable stage order for quality handoffs):

```
Query Understanding        → Understood Query (+ parse quality signals)
    ↓
Retrieval Planner          → Retrieval Plan (+ strategy justification, constraints)
    ↓
Retrieval Engine           → Retrieval Result (+ candidate lifecycle traces, calibrated scores)
    ↓
Evidence Orchestrator      → Evidence Pack (+ evidence quality, coverage, missing-evidence signals)
    ↓
Context Builder            → Context (+ priority selection, compression, citation map, conflicts)
    ↓
Answer Generation          → Answer Result (+ claim grounding, verification, no-answer, citations)
         (logical: Draft → Claim Extraction → Evidence Verification → Citation Resolution → Final)
    ↓
Offline Evaluation (014)   → Quality gates + configuration feedback (offline only)
```

**Accompanying cumulative artifacts** (not stage replacements):

- **Quality Context** — enrichable quality metadata flowing with the request
- **Quality Trace** — append-only diagnostic sections for observability and offline evaluation

**Quality principle**: Each stage maximizes faithful, complete, citable answers by improving the *contract it owns* and enriching Quality Context / Quality Trace — without absorbing downstream responsibilities or overwriting upstream ownership.

---

## 1. Query Understanding Contract

**Owner**: Canonical Query Understanding Owner (016 `query_understanding`)  
**Consumer**: Retrieval Planner (MUST NOT re-parse user intent)

### Contract purpose

Query Understanding produces a canonical **Understood Query** that is the sole intent input to planning. The Planner consumes this contract; it does not re-interpret raw user text as a second parse authority.

### Required quality signals (Understood Query)

| Signal | Meaning |
|--------|---------|
| Parsed intent | Canonical intent class / operation understood from the user request |
| Ambiguity | Whether competing interpretations remain unresolved |
| Confidence | Parse/grounding confidence for intent and entities |
| Extracted entities | Grounded entities available for planning and filtering |
| Extracted constraints | Filterable and scoping constraints (field, scope, recency, etc.) |
| Clarification requirement | Whether clarification is required before reliable planning/execution |
| Degradation reason | Why understanding is partial, unsupported, or degraded (if applicable) |

### Architectural obligations

- Planner MUST treat Understood Query as authoritative for intent, entities, and constraints
- Planner MAY map Understood Query fields into plan strategies and filters; it MUST NOT invent a conflicting intent by re-parsing raw text
- When clarification is required, Planner MUST propagate clarification / non-execution posture rather than fabricating a high-confidence plan
- Application MAY present clarification to the user; stages MUST NOT pretend certainty when understanding signals ambiguity or required clarification
- Domain Packs may inject vocabulary/profiles into Query Understanding; they MUST NOT become a second parse owner

### Quality Context enrichment (Query Understanding)

Ambiguity, confidence, clarification requirement, and degradation reason MUST be written into Quality Context for downstream continuity.

---

## 2. Retrieval Strategy Architecture

**Owner**: Canonical Retrieval Plan Owner (Planner)

Planner decides *what* to retrieve and *why*, without executing retrieval.

### Strategy Registry

A logical catalog of known retrieval strategies available to planning. The registry is the Planner’s source of truth for strategy identity and declared capabilities. Domain Packs may contribute strategy *hints* via published extension points; they MUST NOT privately register production strategies outside the Planner-owned registry contract.

### Strategy Capability Model

Each registered strategy declares architectural capabilities such as:

- Dense / semantic retrieval suitability
- Sparse / keyword retrieval suitability
- Metadata or structured-filter suitability
- Support for filter pushdown
- Expansion compatibility
- Expected evidence locality (broad vs precise)

Capabilities describe *what a strategy can do*, not *how* it is implemented.

### Strategy Selection Policy

Planner selects strategies from the registry using Understood Query signals (intent, entities, constraints, ambiguity, confidence). Selection MUST be explainable: every selected strategy carries a justification tied to parse signals and capability fit.

### Strategy Ordering Policy

Selected strategies are emitted in an ordered list. Order expresses preferred execution priority / complementarity for the Engine, not runtime improvisation. Ordering MUST be deterministic for identical Understood Query and configuration.

### Strategy Degradation Policy

When preferred strategies are unsuitable (low confidence, missing capabilities, unsupported intent, store unavailability known at plan time), Planner MUST degrade explicitly:

- Narrower strategy set
- Clarification-required plan
- Conservative constraints
- Documented degradation reason in plan and Quality Context

Silent substitution of unrelated strategy families is forbidden.

### Strategy Compatibility Rules

- Incompatible strategy combinations MUST NOT be co-selected without an explicit compatibility rationale
- Strategies requiring entities/constraints MUST NOT be selected when those signals are absent or ungrounded
- Meta-strategies (e.g., hybrid-as-composition) MUST expand only into registered component strategies known to the Engine
- Engine executes the plan; Engine MUST NOT re-select strategy families to “improve quality” without traced degradation permitted by plan/execution policy

### Quality signals emitted (Planner)

- Intent class and confidence (from Understood Query, not re-parsed)
- Ordered strategies with selection/ordering justification
- Filterable constraints for pushdown
- Clarification / degradation flags and reasons
- Advisory budget hints (candidate / evidence ceilings)

---

## 3. Retrieval Candidate Lifecycle

**Owner**: Canonical Retrieval Owner (Engine), except where noted

Canonical lifecycle responsibilities (logical order):

```
Candidate Retrieval
    ↓
Candidate Normalization
    ↓
Filter Pushdown
    ↓
Query Expansion
    ↓
Fusion
    ↓
Identity Deduplication
    ↓
Reranking
    ↓
Score Calibration
    ↓
Candidate Selection
```

| Responsibility | Primary owner | Architectural meaning |
|----------------|---------------|------------------------|
| Candidate Retrieval | Engine | Execute plan strategy legs against stores |
| Candidate Normalization | Engine | Normalize heterogeneous candidate shapes into a common candidate contract |
| Filter Pushdown | Engine | Apply plan filters at earliest capable point; residual filters before fusion completes |
| Query Expansion | Engine | Produce plan-allowed query variants; attribute variants in trace |
| Fusion | Engine | Merge multi-leg ranked lists into one candidate pool |
| Identity Deduplication | Engine | Collapse same-identity candidates during/after fusion (first rung of dedup ladder) |
| Reranking | Engine | Optional, disable-safe relevance reordering; distinct from fusion |
| Score Calibration | Engine | Normalize heterogeneous score signals for downstream use (see §4) |
| Candidate Selection | Engine | Budget/cap candidates before Evidence Orchestrator |

**Boundary**: Planner supplies strategies and filters; Engine owns the lifecycle. Evidence Orchestrator MUST NOT re-run primary candidate retrieval. Content-level near-duplicate collapse remains Evidence’s rung (Contract C3).

---

## 4. Score Calibration

**Owner**: Canonical Retrieval Owner (Engine)

### Purpose

Heterogeneous retrieval signals (dense similarity, sparse similarity, metadata quality, reranker output, and related provenance) MUST be made architecturally comparable before downstream ranking and evidence ordering rely on them.

### Obligations

- Calibration is an Engine responsibility occurring after reranking participation is known and before Candidate Selection finalizes the handoff set
- Calibrated scores MUST retain provenance (which signals contributed) in Quality Trace
- Downstream stages MAY use calibrated scores; they MUST NOT invent a second calibration authority
- Disablement or passthrough of calibration MUST be traced as degradation, not hidden
- This specification does **not** define mathematical methods, weights, or algorithms

---

## 5. Evidence Quality Model

**Owner**: Canonical Evidence Owner (Evidence Orchestrator)

Evidence items carry quality signals beyond raw relevance. These are **diagnostic quality signals** for ordering, budgeting, coverage, and offline analysis — not a replacement for stage outputs.

### Evidence quality dimensions (architectural concepts)

| Dimension | Meaning |
|-----------|---------|
| Authority | Relative trustworthiness / source authority signal when available |
| Freshness | Recency / temporal applicability when available |
| Completeness | Whether the item appears truncated or partial relative to its locality |
| Semantic coverage | How much of the request’s semantic need the item appears to address |
| Locality | How tightly the item is scoped to the entities/constraints of the request |
| Confidence | Aggregate evidence-level confidence derived from upstream scores and evidence signals |

### Obligations

- Evidence Pack items SHOULD expose these dimensions when upstream metadata allows; absence MUST be explicit (unknown), not silently treated as high quality
- Ordering MAY use these dimensions together with calibrated relevance; ordering MUST remain stable and explainable
- Evidence quality signals enrich Quality Context / Evidence Trace; they MUST NOT trigger answer generation

---

## 6. Coverage Validation

**Owner**: Canonical Evidence Owner (primary assessment)  
**Consumers**: Context Builder (budget-aware retention), Answer Generation (no-answer / limited-answer decisions), Offline Evaluation (014)

### Purpose

Before answer generation, the pipeline MUST determine whether collected evidence sufficiently covers the user request. Coverage assessment is an **evidence-organization concern**, not an answer-generation concern.

### Obligations

- Evidence Orchestrator MUST emit a coverage assessment into Evidence Pack metadata and Quality Context
- Coverage validation MUST remain separate from Answer Generation ownership
- Context Builder MUST NOT invent coverage; it MAY record how budget changes retained coverage
- Answer Generation consumes coverage signals for no-answer / limited-answer posture; it MUST NOT recompute a competing coverage authority
- Feature 014 remains the offline authority for coverage *scoring against golden expectations*; runtime coverage assessment is a diagnostic continuity signal aligned to that concept, not a second metric definition

---

## 7. Missing Evidence Detection

**Owner**: Canonical Evidence Owner (detection)  
**Continuity**: Context Builder (budget impact), Answer Generation (user-visible posture)

### Evidence sufficiency states

| State | Meaning |
|-------|---------|
| Complete evidence | Coverage assessment indicates the request’s required facets are adequately represented |
| Partial evidence | Some facets are supported; material gaps remain |
| Missing evidence | Required facets are absent or unusable |

### Obligations

- Missing or partial information MUST become an explicit quality signal (Quality Context + Evidence Trace), never a hidden assumption of completeness
- Partial/missing states MUST survive into Answer Generation decisioning (see §15)
- Budget drops that create new gaps MUST update Quality Context (e.g., coverage degraded by omission) without claiming upstream retrieval found the missing facets

---

## 8. Context Priority Model

**Owner**: Canonical Context Owner (Context Builder)

Under token budget, evidence selection follows an architectural priority hierarchy. This is policy structure, not implementation heuristics or algorithms.

### Priority classes (highest → lowest architectural preference to retain)

1. **Conflict evidence** — Items needed to represent disclosed disagreement (both sides when possible)
2. **Primary evidence** — Direct support for the core intent/entities of the request
3. **Supporting evidence** — Secondary confirmation that strengthens primary claims
4. **Contextual evidence** — Adjacent locality that clarifies primary items without being primary itself
5. **Background evidence** — Broadly related but non-essential material
6. **Redundant evidence** — Near-duplicate or low-incremental-value material (first to compress/drop)

### Obligations

- Selection under pressure MUST prefer dropping/compressing lower classes before higher classes
- Conflict evidence MUST NOT be silently reduced to a single side without recording omission resolution (Contract C4)
- Priority class assignment uses Evidence quality signals and conflict markers; Context Builder owns selection, not re-retrieval
- Structural document/section ordering applies **after** priority-preserving selection

---

## 9. Context Compression Policy

**Owner**: Canonical Context Owner

### Compressibility classes

| Class | Architectural rule |
|-------|--------------------|
| Compressible evidence | Background, redundant, and some supporting/contextual items may be compressed when budget requires |
| Non-compressible evidence | Conflict-critical passages and primary evidence required for claim support SHOULD resist compression that would destroy grounding or conflict meaning |

### Preservation rules under compression

- **Citation preservation** — Compressed included blocks MUST retain citation continuity (see §10)
- **Conflict preservation** — Compression MUST NOT erase the distinguishability of conflicting sides that remain included
- **Grounding preservation** — Compression MUST NOT strip the factual anchors needed for claim-level grounding of retained primary/conflict evidence
- Failed compression MUST fall back to include-or-drop with trace; fabricating filler text is forbidden

---

## 10. Citation Continuity

**Owner chain**: Evidence (attribution) → Context (citation map) → Answer Generation (resolution)  
**Invariant**: End-to-end continuity; no stage invents sources

### Citation chain (architectural)

```
Evidence
    ↓
Chunk
    ↓
Document
    ↓
Source
    ↓
Citation
```

| Link | Meaning |
|------|---------|
| Evidence | Selected evidence unit carrying text and attribution |
| Chunk | Underlying chunk identity supporting the evidence unit |
| Document | Parent document identity |
| Source | Origin/source identity used for user-facing reference |
| Citation | Resolved citation object exposed on the answer |

### Obligations

- Every included Context block MUST have a citation map entry resolving through this chain
- Dropped blocks MUST NOT leave dangling citations
- Compression and budgeting MUST preserve chain integrity for retained blocks
- Answer Generation MUST resolve only citations present in Context; unresolved or fabricated citations are continuity failures
- User-visible cited claims MUST resolve to real included evidence units

---

## 11. Conflict Model

**Candidate detection owner**: Evidence Orchestrator  
**Disclosure-ready groups / budget omission records**: Context Builder  
**User-facing disclosure**: Answer Generation

### Conflict categories (architectural)

| Category | Meaning |
|----------|---------|
| Semantic conflict | Contradictory meanings/claims about the same subject |
| Temporal conflict | Disagreement driven by time (older vs newer statements) |
| Authority conflict | Disagreement across differing authority levels |
| Version conflict | Disagreement across document/version identities |
| Duplicate disagreement | Near-duplicate items that nonetheless assert incompatible values |

### Obligations

- Categories are diagnostic labels for continuity and disclosure; they do not create a new owner
- Surviving conflicts MUST remain visible through Context to Answer Generation
- Omission of one side under budget is `resolution: omission`, never agreement
- Answer Generation MUST disclose surviving conflicts; silent side-picking is forbidden

---

## 12. Answer Verification Architecture

**Owner**: Canonical Answer Generation Owner  
**Nature**: Logical responsibilities inside Answer Generation — **not** a separate production pipeline or owner

```
Answer Draft
    ↓
Claim Extraction
    ↓
Evidence Verification
    ↓
Citation Resolution
    ↓
Final Answer
```

| Logical responsibility | Meaning |
|------------------------|---------|
| Answer Draft | Produce candidate answer content from Context and instructions |
| Claim Extraction | Identify atomic claims requiring grounding |
| Evidence Verification | Check each claim against included evidence |
| Citation Resolution | Bind supported claims to Context citation map entries |
| Final Answer | Emit Answer Result with disclosures, limitations, no-answer posture, and resolved citations |

Verification MUST NOT re-retrieve, re-plan, or assemble a second context. It operates only on Context + draft.

---

## 13. Claim-Level Grounding

**Owner**: Answer Generation (verification responsibilities)

- Grounding applies at **claim level**, not only at whole-answer level
- A claim without supporting included evidence MUST NEVER be marked or presented as grounded
- Unsupported claims MUST be removed, rewritten to limited/no-answer posture, or explicitly flagged per Answer Generation policy — they MUST NOT silently remain as grounded facts
- Whole-answer “generally looks fine” is insufficient when any claim lacks evidence

---

## 14. Hallucination Prevention Chain

Prevention is a complete architectural chain. Each stage contributes independently; there is no separate “hallucination owner.”

| Stage | Contribution |
|-------|--------------|
| Query Understanding | Do not fabricate grounded entities/fields; signal ambiguity and clarification |
| Planner | Do not invent unconstrained high-confidence plans for unresolvable intent; propagate degradation |
| Retrieval Engine | Do not invent candidates for failed legs; do not silently drop filters; trace degradation |
| Evidence Orchestrator | Do not fabricate evidence text; emit partial/missing coverage honestly |
| Context Builder | Do not fabricate filler to fill budget; preserve conflict and citation integrity |
| Answer Generation | No-answer / limited-answer when evidence insufficient; cite only mapped sources |
| Verification (logical, under Answer Generation) | Reject or flag ungrounded claims at claim level before Final Answer |

Contract C7 binds this chain as normative continuity.

---

## 15. No-Answer Decision Model

**Decision owner**: Answer Generation  
**Signal providers**: Query Understanding, Planner, Evidence (coverage/missing), Context (budget/conflicts)

Architectural no-answer / limited-answer **conditions** (responsibility to recognize signals — not implementation logic):

| Condition | Primary signal source | Architectural expectation |
|-----------|----------------------|---------------------------|
| No evidence | Engine/Evidence empty | Explicit no-answer; no generative fill-in |
| Weak evidence | Evidence quality / confidence | Limited-answer or no-answer; no overconfident claims |
| Conflicting evidence | Context conflicts | Disclose conflict; may refuse a single definitive answer |
| Partial evidence | Missing-evidence / coverage | Answer only supported facets; state gaps |
| Ambiguous query | Understood Query / Planner | Clarification or non-definitive posture |
| Out-of-domain | Query Understanding / Planner | Unsupported / out-of-scope posture |
| Restricted answer | Policy / Domain Pack constraints via Application | Refuse or constrain per policy without fabricating |

Answer Generation owns the decision; upstream stages own honest signals. No stage may hide a no-answer condition by inventing evidence.

---

## 16. Quality Trace

**Purpose**: Diagnostics, observability, offline evaluation (014). Append-only sections; not a user-facing API replacement.

| Trace section | Produced by |
|---------------|-------------|
| Plan Trace | Planner |
| Retrieval Trace | Engine (candidate retrieval / normalization) |
| Expansion Trace | Engine |
| Fusion Trace | Engine |
| Rerank Trace | Engine |
| Evidence Trace | Evidence Orchestrator |
| Context Trace | Context Builder |
| Generation Trace | Answer Generation |
| Verification Trace | Answer Generation (logical verification) |

### Obligations

- Each stage MUST append its section without erasing upstream sections
- Traces SHOULD include degradation reasons, filter application points, coverage/missing-evidence states, budget omissions, and grounding/verification outcomes as applicable
- Offline evaluation MAY consume Quality Trace; runtime ownership of stages does not move to evaluation

---

## 17. Stage Quality Metrics

Architecture-level measurable metrics (for review, observability, and offline alignment). These are **not** a redesign of feature 014’s golden metrics; 014 remains offline authority for coverage, faithfulness, and completeness.

### Query Understanding

- Intent parse reliability (successful grounded intent vs clarification/degradation)
- Entity grounding honesty (no fabricated entities)

### Planner

- Intent fidelity to Understood Query (no re-parse drift)
- Strategy alignment (selected strategies justified by capabilities and parse signals)

### Engine

- Retrieval recall (relevant candidates present under plan constraints — offline/eval aligned)
- Filter effectiveness (declared filters applied or explicitly residual/unapplied)
- Calibration honesty (heterogeneous scores provenance retained)

### Evidence

- Dedup effectiveness (redundant collapse without citation attribution loss)
- Evidence coverage (complete / partial / missing states accurate)
- Evidence quality signal completeness (unknown vs populated dimensions)

### Context

- Token utilization (budget used vs available without overflow)
- Citation retention (included blocks fully mapped through citation chain)
- Priority fidelity (higher priority classes retained preferentially under pressure)

### Answer Generation / Verification

- Grounding rate (claims grounded at claim level)
- Unsupported claim rate (ungrounded claims escaping as grounded)
- Citation correctness (resolved citations match Context map and chain)
- Conflict disclosure rate when conflicts survive
- No-answer correctness when no/weak/missing evidence conditions apply

---

## 18. Quality Feedback Loop

**Offline authority**: Feature 014  
**Runtime owners**: Unchanged (016)

```
Production / shadow answers
    ↓
Offline Evaluation (014) — coverage, faithfulness, completeness (+ stage metrics as diagnostics)
    ↓
Configuration / policy feedback (thresholds, pack profiles, strategy registry hints, budget policies)
    ↓
Runtime stages consume updated configuration via Composition — ownership unchanged
```

### Obligations

- Evaluation MUST remain offline; it MUST NOT become a request-path owner
- Feedback may improve configuration, Domain Pack profiles, and strategy registry hints
- Feedback MUST NOT create a parallel retrieval/answer path or move ownership to the evaluator
- Disagreement between stage-local heuristics and 014 gates: **014 wins** for release/cutover quality authority

---

## 19. Extension Points

Extensions preserve contracts and sole ownership. Domain Packs and provider adapters extend; they do not capture core orchestration.

| Stage | Extension point examples (architectural) |
|-------|------------------------------------------|
| Query Understanding | Vocabulary / entity catalogs, field profiles, clarification templates |
| Planner | Strategy registry hints, constraint vocabularies, selection policy profiles |
| Engine | Retriever adapters, expansion adapters, reranker providers, store capability declarations |
| Evidence | Evidence quality signal enrichers, conflict-candidate detectors (under Evidence owner) |
| Context | Compression adapters, priority profile packs, stitch ordering profiles |
| Answer Generation | Prompt capability modules, disclosure wording packs, grounding policy profiles |

### Extension rules

- Extensions MUST honor Contracts C1–C10 and sole-owner boundaries
- Extensions MAY tighten quality (more conservative no-answer, stricter filters); they MUST NOT weaken hallucination prevention, citation continuity, filter continuity, or modularity freeze
- Composition wires extensions; stages remain owners of their contracts

---

## 20. Quality Context

**Purpose**: Cumulative quality metadata flowing through the pipeline. Enriches; does **not** replace stage outputs (Understood Query, Plan, Retrieval Result, Evidence Pack, Context, Answer Result).

### Example accumulated information

- Ambiguity
- Retrieval confidence
- Coverage (complete / partial / missing)
- Evidence confidence
- Conflict summary
- Citation completeness
- Budget usage
- Grounding status
- Degradation history

### Obligations

- Every stage MAY enrich Quality Context
- No stage may overwrite upstream ownership fields; enrichments are additive or explicitly scoped to the enriching stage’s namespace
- Downstream stages consume Quality Context for decisions they already own (e.g., Answer Generation no-answer), not to seize upstream responsibilities
- Quality Context and Quality Trace are complementary: Context = current cumulative state; Trace = historical sectioned diagnostics

---

## Stage Quality Architecture (Summary Obligations)

### Retrieval Planner

- Consume Understood Query without re-parsing intent
- Apply Strategy Registry, Capability Model, Selection/Ordering/Degradation/Compatibility policies
- Emit justified ordered strategies and filterable constraints
- MUST NOT execute retrieval, expand against indexes, rerank, assemble evidence, verify claims, or generate answers

### Retrieval Engine

- Own candidate lifecycle through Candidate Selection, including score calibration
- Honor plan strategies; traced degradation only
- Emit Retrieval Result + lifecycle traces; enrich Quality Context
- MUST NOT re-plan intent, organize Evidence Packs, assemble LLM context, or generate answers

### Evidence Orchestrator

- Own Evidence Pack, content-level dedup, evidence ordering, evidence quality model, coverage validation, missing-evidence states, conflict candidates
- MUST NOT primary-retrieve, assemble final LLM context, or generate answers

### Context Builder

- Own priority-based selection, compression policy, citation map, disclosure-ready conflicts, structural ordering, final dedup safety-net
- MUST NOT call the generative model for the user answer or invent citations/coverage

### Answer Generation (incl. logical verification)

- Own draft → claim extraction → evidence verification → citation resolution → final answer
- Own claim-level grounding, conflict disclosure, no-answer decisions, Answer Result
- MUST NOT re-retrieve, re-rank, or mutate upstream evidence contracts except answer-local formatting

---

## Cross-Stage Quality Contracts

### Contract C1 — Strategy Alignment

Planner strategy choices MUST be executable by the Engine without reinterpretation of intent. Engine MAY degrade a strategy leg but MUST NOT substitute an unplanned strategy family without traced degradation.

### Contract C2 — Filter Pushdown Continuity

Filters declared in the plan MUST be applied (pushdown or residual) before Evidence Pack formation, or listed as unapplied with reason. Silent filter loss is forbidden.

### Contract C3 — Deduplication Ladder

1. Engine: identity-level dedup in candidate lifecycle  
2. Evidence Orchestrator: exact / near-duplicate content collapse  
3. Context Builder: final safety-net under budget pressure  

Later layers MUST NOT destroy citation attribution.

### Contract C4 — Conflict Continuity

Conflict candidates and categorized conflicts remain attributable through Context. Answer Generation discloses survivors. Budget omission ≠ agreement.

### Contract C5 — Citation Continuity

Evidence → Chunk → Document → Source → Citation remains intact for every included block through compression and budgeting. Answers cite only mapped citations.

### Contract C6 — Token Efficiency

Prefer early filtering, dedup, and policy-governed compression over late truncation that breaks citations or conflict counterparts.

### Contract C7 — Hallucination Prevention Chain

Normative multi-stage chain in §14, including logical verification under Answer Generation. Fabricated certainty is forbidden at every stage.

### Contract C8 — Modularity Freeze

No parallel quality pipeline, second retrieval path, or second answer path. Domain heuristics via extension points only. 016 sole-owner and M0 freeze bind.

### Contract C9 — Understood Query Authority

Planner and downstream stages MUST NOT re-parse user intent as a competing authority. Clarification and degradation signals from Query Understanding MUST propagate.

### Contract C10 — Coverage & Missing-Evidence Continuity

Complete / partial / missing evidence states and coverage assessment MUST flow via Evidence → Quality Context → Answer decisions. Answer Generation MUST NOT invent completeness. Offline 014 remains evaluation authority for golden coverage scoring.

### Contract C11 — Quality Context / Trace Continuity

Stages enrich Quality Context and append Quality Trace sections without erasing upstream ownership. Evaluation consumes; it does not own runtime.

### Contract C12 — Claim-Level Grounding Continuity

Ungrounded claims MUST NOT appear as grounded in Final Answer. Verification responsibilities enforce this inside Answer Generation ownership.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Architect Validates Stage Quality Boundaries (Priority: P1)

A platform architect assigns every quality concern in this specification to exactly one primary owning stage (plus allowed safety-net layers), including Query Understanding handoff, strategy architecture, candidate lifecycle steps, score calibration, coverage validation, missing evidence, context priority/compression, citation chain, conflict categories, claim-level grounding, verification responsibilities, Quality Context/Trace, and feedback loop — without inventing a new production owner.

**Why this priority**: Boundary clarity is the prerequisite for modular quality work.

**Independent Test**: For each concern in §§1–20, a reviewer names the primary owner and cites the matching section and contract.

**Acceptance Scenarios**:

1. **Given** “filter pushdown” or “score calibration”, **When** reviewed, **Then** primary ownership is Retrieval Engine; Planner supplies filters/strategies only.
2. **Given** “coverage validation” or “missing evidence”, **When** reviewed, **Then** primary ownership is Evidence Orchestrator; Answer Generation consumes signals only (Contract C10).
3. **Given** “claim-level grounding” or “answer verification”, **When** reviewed, **Then** ownership remains Answer Generation as logical sub-responsibilities — not a new pipeline (Contract C12 / §12).
4. **Given** “Understood Query signals”, **When** reviewed, **Then** Query Understanding owns production of the contract; Planner consumes without re-parsing (Contract C9).

---

### User Story 2 — Quality Engineer Maps Failures to the Correct Stage (Priority: P1)

A quality engineer attributes bad answers (missed filters, false completeness, hidden conflicts, ungrounded claims, broken citations, ignored ambiguity) to the earliest broken contract using Quality Context / Quality Trace concepts.

**Why this priority**: Mis-attributed bugs cause the wrong stage to be “fixed.”

**Independent Test**: Present vignettes spanning filter loss, missing-evidence hidden as complete, silent conflict, uncited claim, re-parse drift. Reviewer maps each to C1–C12.

**Acceptance Scenarios**:

1. **Given** an entity filter in the plan ignored in results, **When** diagnosed, **Then** failure maps to Engine filter continuity (C2) or Planner if never declared.
2. **Given** a definitive answer despite partial/missing evidence signals, **When** diagnosed, **Then** failure maps to Answer no-answer decisioning (C10/C7) or Evidence if signals were dishonest.
3. **Given** a claim marked grounded with no supporting included evidence, **When** diagnosed, **Then** failure maps to claim-level grounding / verification (C12).
4. **Given** Planner intent disagreeing with Understood Query without degradation reason, **When** diagnosed, **Then** failure maps to C9.

---

### User Story 3 — Product Owner Sees Measurable Quality Outcomes (Priority: P1)

A product owner understands user-visible quality (grounded completeness, fewer fabrications, conflict honesty, explicit gaps/no-answer) and that feature 014 remains the offline gate, with this architecture supplying continuity and stage metrics for diagnosis — not competing score definitions.

**Why this priority**: Architecture must validate as outcomes, not as internals.

**Independent Test**: Map SC-001–SC-010 to user-visible or offline checks without naming frameworks.

**Acceptance Scenarios**:

1. **Given** Success Criteria, **When** reviewed by a product owner, **Then** each is understandable without code modules.
2. **Given** feature 014 dimensions, **When** this architecture is applied, **Then** 014 remains regression authority and the feedback loop (§18) does not move evaluation onto the request path.

---

### User Story 4 — Maintainer Rejects Modularity-Breaking Shortcuts (Priority: P2)

A maintainer rejects proposals that merge stages, add a second retrieval/answer path “for quality,” move coverage into Answer Generation ownership, or make offline eval a runtime owner.

**Why this priority**: Quality pressure commonly causes architectural regression.

**Independent Test**: Hypothetical dual path or mega-stage is rejectable via C8 and 016 M0 freeze; eval-on-request-path rejectable via §18.

**Acceptance Scenarios**:

1. **Given** a parallel quality-only retrieval path, **When** C8 is applied, **Then** it is out of bounds without superseding 016 governance.
2. **Given** a proposal that Answer Generation recomputes coverage as sole authority, **When** C10 is applied, **Then** it is rejected.
3. **Given** a proposal to run 014 evaluators inline as a production gate owner, **When** §18 is applied, **Then** it is rejected as ownership violation.

---

### User Story 5 — Architect Validates Quality Context and Trace Continuity (Priority: P2)

An architect confirms Quality Context accumulates ambiguity, coverage, conflicts, budget, grounding, and degradation history, and that Quality Trace contains the sectioned diagnostics in §16, without replacing Plan/Evidence/Context/Answer contracts.

**Why this priority**: Without cumulative continuity, stage metrics and offline feedback cannot attribute defects.

**Independent Test**: Walk a sample request narrative and list which stage enriches which Quality Context fields and which Trace section is appended.

**Acceptance Scenarios**:

1. **Given** a partial-evidence request under budget pressure, **When** continuity is checked, **Then** Evidence sets partial/missing, Context records budget impact, Answer reflects limited/no-answer — all visible in Quality Context.
2. **Given** disabled reranking, **When** Trace is inspected, **Then** Rerank Trace records disablement/degradation and Fusion Trace remains present.

---

### Edge Cases

- Clarification required from Query Understanding → Planner propagates; stages MUST NOT invent certainty; Answer/Application may clarify.
- All Engine legs empty → Evidence/Context empty; Answer no-evidence no-answer; no parametric fill-in.
- Rerank or calibration disabled → traced degradation; contracts remain honest.
- Expansion creates near-duplicates → Evidence dedup + Context safety-net (C3).
- Budget drops one conflict side → omission resolution; Answer MUST NOT claim agreement.
- Compression would destroy primary/conflict grounding anchors → treat as non-compressible or drop with trace; never fabricate.
- Domain Pack conflicts with core contracts → core wins; packs may tighten only.
- Offline eval (014) vs stage heuristic disagreement → 014 wins for release/cutover authority.
- Out-of-domain / restricted → no-answer or restricted posture from signals; no fabricated domain knowledge.
- Partial evidence with high calibrated scores on irrelevant facets → coverage/missing-evidence signals MUST still reflect request facet gaps (scores alone ≠ completeness).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Architecture MUST define quality obligations for Query Understanding (handoff), Retrieval Planner, Retrieval Engine, Evidence Orchestrator, Context Builder, and Answer Generation (including logical verification) without adding a new production owner for “quality,” coverage, or evaluation-on-request-path.
- **FR-002**: Architecture MUST assign primary ownership for: query-understanding handoff, planner robustness, strategy registry/capability/selection/ordering/degradation/compatibility, retrieval lifecycle steps, score calibration, evidence quality dimensions, coverage validation, missing-evidence states, evidence ordering, conflict categories, context priority, context compression, citation chain, claim-level grounding, no-answer conditions, Quality Context, Quality Trace, stage metrics, offline feedback, and extension points.
- **FR-003**: Query Understanding MUST emit Understood Query quality signals (parsed intent, ambiguity, confidence, entities, constraints, clarification requirement, degradation reason). Planner MUST consume this contract without re-parsing user intent (C9).
- **FR-004**: Planner MUST implement Strategy Registry, Capability Model, Selection, Ordering, Degradation, and Compatibility policies architecturally, with explainable strategy justification, and MUST NOT execute retrieval.
- **FR-005**: Engine MUST own the candidate lifecycle (retrieval → normalization → filter pushdown → expansion → fusion → identity dedup → reranking → score calibration → candidate selection) and MUST NOT re-plan intent.
- **FR-006**: Engine MUST own score calibration of heterogeneous signals before candidate handoff, with provenance in Quality Trace, without prescribing mathematics.
- **FR-007**: Evidence Orchestrator MUST own Evidence Quality Model dimensions (authority, freshness, completeness, semantic coverage, locality, confidence), coverage validation, and complete/partial/missing evidence states as explicit signals.
- **FR-008**: Context Builder MUST own Context Priority Model and Context Compression Policy, including compressible vs non-compressible classes and preservation of citation, conflict, and grounding anchors.
- **FR-009**: Citation continuity MUST follow Evidence → Chunk → Document → Source → Citation through compression and budgeting (C5).
- **FR-010**: Conflict model MUST categorize semantic, temporal, authority, version, and duplicate-disagreement conflicts while preserving Evidence → Context → Answer ownership split (C4).
- **FR-011**: Answer Generation MUST include logical verification responsibilities (draft → claim extraction → evidence verification → citation resolution → final) without creating a second pipeline.
- **FR-012**: Grounding MUST be claim-level; claims without supporting included evidence MUST NEVER appear as grounded (C12).
- **FR-013**: Hallucination prevention MUST be specified as the full chain in §14 (C7).
- **FR-014**: No-answer decision model MUST distinguish no evidence, weak evidence, conflicting evidence, partial evidence, ambiguous query, out-of-domain, and restricted answer — with Answer Generation deciding from upstream signals (§15).
- **FR-015**: Architecture MUST define Quality Trace sections (Plan, Retrieval, Expansion, Fusion, Rerank, Evidence, Context, Generation, Verification) and cumulative Quality Context (§§16, 20; C11).
- **FR-016**: Architecture MUST define stage quality metrics per §17 without redefining feature 014 golden metrics.
- **FR-017**: Feature 014 MUST remain offline evaluation authority; feedback loop MAY influence configuration only; runtime ownership unchanged (§18).
- **FR-018**: Each stage MUST have explicit extension points that preserve contracts and sole ownership (§19).
- **FR-019**: Cross-stage Contracts C1–C12 MUST be normative.
- **FR-020**: Architecture MUST remain compatible with 015 dual-run transition (no permanent second answer path), 016 sole-owner/M0 freeze, and 017 ingest orthogonality.
- **FR-021**: Degradation modes MUST be traced; silent substitution of unplanned behavior is forbidden.
- **FR-022**: This feature’s specify-phase artifacts are architecture specification and review checklists only — no implementation designs.

### Key Entities

- **Understood Query**: Canonical parse contract with intent, ambiguity, confidence, entities, constraints, clarification requirement, degradation reason.
- **Strategy Registry / Capability Model**: Planner-owned catalog of strategies and their architectural capabilities.
- **Retrieval Plan**: Ordered justified strategies, filters, budgets hints, clarification/degradation posture.
- **Candidate Lifecycle State**: Engine-owned progression through lifecycle responsibilities ending in selected candidates.
- **Calibrated Score Set**: Engine-owned normalized score view with provenance for downstream use.
- **Evidence Pack**: Evidence items plus quality dimensions, coverage assessment, missing-evidence state, conflict candidates.
- **Evidence Sufficiency State**: Complete, partial, or missing.
- **Context**: Budgeted ordered blocks, citation map, conflicts, compression metadata.
- **Context Priority Class**: Conflict, primary, supporting, contextual, background, redundant.
- **Citation Chain Link**: Evidence ↔ Chunk ↔ Document ↔ Source ↔ Citation.
- **Conflict Category**: Semantic, temporal, authority, version, duplicate disagreement.
- **Answer Result**: Final answer with claim-level grounding outcomes, citations, disclosures, no-answer posture.
- **Quality Context**: Cumulative enrichable quality metadata accompanying stage outputs.
- **Quality Trace**: Append-only sectioned diagnostics for observability and offline evaluation.
- **Stage Quality Metric**: Architecture-level measurable indicator per stage (§17).
- **Extension Point**: Published stage extension surface that cannot capture ownership.
- **Cross-Stage Quality Contract**: Normative continuity rule (C1–C12).

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Respect Clean Architecture and 016 dependency boundaries.
- **NFR-002**: Stage boundaries remain independently testable at contract level (Understood Query, Plan, Retrieval Result, Evidence Pack, Context, Answer Result), with Quality Context/Trace as accompanying artifacts.
- **NFR-003**: External providers remain swappable; architecture MUST NOT hard-bind vendors.
- **NFR-004**: Retrieval-augmented answers MUST preserve source citations as first-class outcomes.
- **NFR-005**: Prompt instructions affecting grounding or conflict disclosure MUST be versioned when changed.
- **NFR-006**: Observability MUST expose Quality Trace / Quality Context fields sufficient for defect attribution; correlation identifiers remain required at boundaries.
- **NFR-007**: Secrets MUST NOT appear in architecture artifacts.
- **NFR-008**: Delivery artifact for this phase is architecture specification; implementation completeness is not a success measure here.
- **NFR-009**: Determinism — identical contract inputs and configuration yield attributable stage outputs and stable strategy ordering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer maps all quality concerns in §§1–20 to a primary owning stage in under 20 minutes using only this specification.
- **SC-002**: For at least 12 bad-answer vignettes spanning filter loss, re-parse drift, false completeness, conflict silence, broken citation chain, and ungrounded claims, reviewers attribute ≥90% to the correct earliest broken contract (C1–C12).
- **SC-003**: Architecture review confirms zero new production owners and zero new parallel retrieval/answer paths vs 016 ownership registry.
- **SC-004**: Feature 014 remains declared offline authority for coverage, faithfulness, and completeness; this spec introduces no competing golden metric definitions.
- **SC-005**: Stakeholders can describe user-visible behavior for no evidence, partial evidence, conflicting evidence, ambiguous query, and uncited/ungrounded claims without referring to code.
- **SC-006**: Stakeholders can state Context priority class order and compressible vs non-compressible preservation rules without naming algorithms.
- **SC-007**: At least one modularity anti-pattern (mega-stage, dual quality path, eval-as-runtime-owner) is rejectable by citing C8 and §18.
- **SC-008**: Reviewers can list Quality Trace sections and name which stage appends each section.
- **SC-009**: Reviewers can explain that grounding is claim-level and that unsupported claims cannot be marked grounded.
- **SC-010**: Reviewers can describe the 014 → configuration feedback loop and confirm evaluation stays offline.

## Assumptions

- Features 004 and 009–013 remain the libraries/stages being quality-hardened; this spec overlays quality architecture.
- Feature 016 ownership and M0 freeze remain authoritative; this refinement does not reopen owner selection.
- Feature 014 remains offline golden/regression authority; stage metrics here are architectural diagnostics aligned to, not replacing, 014.
- Feature 015 dual-run Answer traffic remains transitional and is not a permanent second quality path.
- Feature 017 does not constrain answer-quality contracts beyond shared platform observability expectations.
- Score calibration, coverage validation, and verification are concerns under existing owners (Engine, Evidence, Answer Generation respectively) — not new owners.
- Conflict detection remains split: candidates/categories at Evidence; disclosure-ready groups and budget omission at Context; user disclosure at Answer Generation.
- Expansion includes Engine query expansion and Evidence adjacent-context enrichment; both are policy-gated and must honor dedup/citation contracts.
- Default grounding posture: unsupported claims cannot be presented as grounded; hard-block vs rewrite-to-limited-answer is Answer Generation policy detail that does not change ownership.
- Domain Packs may tighten filters, synonyms, disclosure wording, and strategy hints; they may not weaken C2, C5, C7, C8, C9, C10, or C12.
- Frozen external answer API need not expose full Quality Context/Trace; internal continuity may exceed external fields.
- Thresholds, formulas, and provider benchmarks remain deferred to future plan/implement phases and are intentionally absent here.

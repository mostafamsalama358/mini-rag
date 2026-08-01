# Feature Specification: RAG Evaluation Framework

**Feature Branch**: `019-rag-evaluation-framework`

**Created**: 2026-07-18

**Updated**: 2026-07-18

**Status**: Draft

**Input**: User description: "Design complete evaluation framework for production RAG covering golden datasets, regression testing, retrieval/planner/answer/citation evaluation, hallucination detection, offline and online benchmarks, and production monitoring. Define metrics (Recall, Precision, MRR, NDCG, Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate, Latency, Cost). Design evaluation pipeline, CI integration, regression gates, benchmark datasets, reporting, and dashboards. Focus on evaluation architecture. No implementation."

**Artifact type**: Evaluation architecture specification. Implementation, algorithms, code, provider selection, dashboards as concrete products, and sprint planning are out of scope.

---

## Scope

### In Scope

- End-to-end **evaluation architecture** for production RAG quality, reliability signals, and operational health
- Golden dataset model and governance for multi-stage evaluation (retrieval, planner, answer, citation, hallucination)
- Offline evaluation pipeline and offline benchmarks
- Online / shadow evaluation and production monitoring contracts
- Canonical metric catalog: Recall, Precision, MRR, NDCG, Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate, Latency, Cost
- Regression testing model, CI integration contracts, and release regression gates
- Benchmark dataset tiers and reporting / dashboard information architecture
- Clear relationship to features 014 (existing offline golden seed), 016 (sole-owner / M0 freeze), and 018 (stage quality contracts and diagnostic metrics)

### Out of Scope

- Implementation code, libraries, formulas, class diagrams, file layout, or task breakdown
- Changing production ownership of Query Understanding, Planner, Engine, Evidence, Context, or Answer Generation
- Introducing a parallel production answer or retrieval path for “evaluation mode”
- Redefining frozen external `/answer` API field-level contracts (015)
- Ingest / chunking / document-intelligence redesign (006 / 007 / 017 remain orthogonal except as evaluation *subjects*)
- Concrete BI tool, observability vendor, or CI product selection
- Authoring UI for golden datasets (versioned dataset artifacts are in scope as a model; tooling UX is not)
- Concrete judge implementations, threshold values, or scoring formulas

---

## Relationship to Existing Features

| Feature | Relationship |
|---------|--------------|
| 014 Answer Quality | **Seed capability**. Coverage, Faithfulness, and Completeness golden scoring and offline regression tracking remain valid metric semantics. This feature **extends** evaluation into a complete multi-stage framework (retrieval IR metrics, planner evaluation, citation accuracy, hallucination rate, latency/cost, online/monitoring). 014 does not remain the sole evaluation architecture authority once this feature is adopted. |
| 018 RAG Quality Architecture | **Contract source**. Stage quality obligations, Quality Context / Trace, and diagnostic stage metrics feed evaluation. This feature does **not** redefine 018 stage ownership or create a sixth production quality owner. On release-gate disagreement between stage heuristics and evaluation gates, **evaluation gates win**. |
| 016 Architecture Consolidation | **Governance baseline**. Evaluation remains a non-production-path capability (offline / CI / shadow / monitoring). No new sole owner for retrieval or answer. M0 freeze applies: no parallel production implementations. Metric **primary owners** below are attribution owners for evaluation regression — they map to existing 016 production stage owners and do not create new production stages. |
| 015 Unified Pipeline Migration | Dual-run / cutover remains the answer traffic vehicle; evaluation may consume dual-run / shadow / canary outputs as experiment inputs but MUST NOT become a second answer owner. |
| 009–013 Stage libraries | Evaluation **subjects**. Planner, Engine, Evidence, Context, and Answer outputs are scored; stage owners remain unchanged. |
| 004 Query Understanding | Evaluation may score parse / intent handoff quality where golden labels exist; Query Understanding ownership unchanged. |
| 002 Domain Packs | Domain-specific labels and expected sources enter via datasets and Domain Pack profiles — not hard-coded into evaluation architecture. |

**Authority rule**: Feature **019** is the evaluation architecture authority. Feature **014** metric definitions for coverage / faithfulness / completeness are preserved unless explicitly revised here. Feature **018** stage metrics remain diagnostic and offline-alignable; they do not replace golden/regression gates.

---

## Design Principles

1. **Evaluation is not a production stage** — scoring, gating, and monitoring never own user-facing answer generation.
2. **Exactly one primary owner per failed metric** — regression attribution names a single primary stage owner; supporting stages may appear as secondary context only.
3. **Stage-attributable defects** — every failed metric MUST map through the Metric Ownership table and Error Taxonomy so regressions are actionable (aligns with 018 defect attribution).
4. **Offline gates before online trust** — release decisions prefer offline golden / benchmark gates; online signals detect drift after release.
5. **Metric honesty** — N/A is preferred over false zeros when labels or citations are absent; no-answer postures are scored separately from faithfulness.
6. **Judge-stable metrics** — metric identities and semantics remain stable across interchangeable judges; judge choice MUST NOT redefine metric meaning.
7. **Dataset-driven domain content** — domain facts enter only through versioned datasets and Domain Packs.
8. **Comparable runs** — every evaluation run is keyed, reproducible against dataset version, experiment role, and rich configuration fingerprint, and diffable against a baseline.
9. **Cost and latency are first-class** — quality gates MUST NOT ignore resource tradeoffs; cost/latency are reported alongside quality metrics.
10. **Sole-path compatibility** — evaluation consumes canonical pipeline outputs / Quality Trace; it MUST NOT invent a second retrieval or answer path.

---

## Evaluation Lifecycle

End-to-end evaluation ecosystem (architecture flow — not a production request path):

```
Dataset (curate → approve → freeze)
        │
        ▼
Evaluation (profile + judges + subjects)
        │
        ▼
Reports (item / run / trend / slice / executive)
        │
        ▼
Regression Gates (profile-bound decisions)
        │
        ▼
Release (champion acceptance)
        │
        ▼
Shadow / Canary / Challenger observation
        │
        ▼
Production Monitoring (drift + alerts)
        │
        ▼
Dataset Evolution (lineage → changelog → new freeze)
```

**Purpose**: Show that datasets, evaluation, gates, release confidence, live observation, and dataset evolution form one closed architectural loop — without making evaluation a production pipeline stage.

---

## Evaluation Architecture Overview

Logical evaluation system (not a production request path):

```
Versioned Datasets / Benchmarks
        │
        ▼
Evaluation Orchestrator (profile-selected mode)
        │
        ├── Judge Layer (Rule | LLM | Human | Hybrid)
        ├── Retrieval Evaluator      → Recall, Precision, MRR, NDCG
        ├── Planner Evaluator        → Plan Fidelity, Strategy Alignment
        ├── Answer Evaluator         → Faithfulness, Groundedness, Completeness
        ├── Citation Evaluator       → Citation Accuracy
        ├── Hallucination Detector   → Hallucination Rate
        └── Ops Evaluator            → Latency, Cost
        │
        ▼
Run Store (results + provenance + diffs)
        │
        ├── Regression Gates ──► CI / Release decision
        ├── Experiment Compare (Baseline / Candidate / Champion / Challenger / Shadow / Canary)
        └── Reports & Dashboards (+ alerts, slices, composite scores)
```

**Modes**:

| Mode | Purpose | Traffic |
|------|---------|---------|
| Offline golden / regression | Deterministic release gates | Fixture / recorded / replayed pipeline outputs |
| Offline benchmark | Broader capability comparison across versions | Larger labeled corpora; profile-bound gating |
| Online shadow | Live-like quality on non-user-visible dual/shadow path | Shadow or dual-run outputs (015-compatible) |
| Production monitoring | Drift, latency, cost, safety proxies | Sampled production telemetry + Quality Trace; no request-path ownership |

---

## 1. Golden Dataset Architecture

### Dataset tiers

| Tier | Role | Typical use |
|------|------|-------------|
| **Core Golden** | Small, high-trust, curated | PR / merge regression gates |
| **Extended Golden** | Broader labeled set | Nightly / pre-release offline suite |
| **Adversarial / Probe** | Hallucination, conflict, missing-evidence, no-answer | Safety and edge-case gates |
| **Benchmark Corpus** | Larger IR / answer corpora | Offline benchmarks and trend studies |
| **Online Sample Labels** | Sparse human or heuristic labels on live traffic | Drift detection (not primary release authority) |

### Dataset record (logical)

Each evaluation item MUST be able to carry, as applicable:

- Stable item identity and dataset version
- Query text (and optional Understood Query labels)
- Relevance labels for retrieval (graded or binary) at document/chunk granularity
- Expected planner signals (intent class, required strategies/constraints) when planner evaluation applies
- Expected sources / evidence identities for coverage-style checks
- Expected answer facets for completeness
- Optional reference answer for groundedness / semantic match modes
- Citation expectations (which claims require which sources)
- Labels for no-answer / abstention correctness
- Match mode declaration (exact / semantic / graded relevance)
- Slice tags (see Slice Architecture)
- Per-metric thresholds override (optional; else profile / gate policy)

### Dataset Governance

Governance is mandatory for any dataset used in blocking gates.

#### Lifecycle

| Phase | Meaning |
|-------|---------|
| **Draft** | Editable; not eligible for blocking gates |
| **In Review** | Proposed for approval; change-controlled |
| **Approved** | Accepted for non-blocking or designated profiles |
| **Frozen** | Immutable content identity for a version; required for PR/Release comparability |
| **Retired** | No longer eligible for new blocking runs; retained for historical lineage |
| **Superseded** | Replaced by a newer frozen version; old version remains readable for diffs |

#### Approval

- Blocking tiers (Core Golden, and any dataset bound to Release profile) MUST be explicitly approved before freeze
- Approval records WHO approved, WHAT version, and WHY (changelog reference)
- Domain Pack owners approve domain-specific label content; evaluation architects approve structural/schema fitness

#### Freeze

- A frozen dataset version MUST NOT mutate item labels or identities in place
- Corrections require a new dataset version (lineage link to prior freeze)
- Evaluation profiles that gate releases MUST pin frozen dataset versions

#### Retirement

- Retirement is explicit and recorded; retired versions remain available for historical run interpretation
- Retirement MUST state successor version when one exists

#### Compatibility

- Dataset schema compatibility is versioned; runs MUST record whether the dataset schema is compatible with the evaluator contract version
- Incompatible schema ⇒ fail closed for blocking profiles (never silent PASS)

#### Lineage

- Each dataset version MUST declare parent/predecessor version (if any), source of labels, and derivation notes (e.g., split from Extended → Core)
- Lineage supports audit of how a golden item entered a blocking set

#### Changelog

- Every version bump MUST include a human-readable changelog: added/removed/changed items, label edits, slice-tag changes, intended gate impact
- Loosening labels or removing failing items from Core Golden is a governed change (explicit review)

#### Reproducibility guarantees

- A run that cites `dataset_version = X` MUST be re-interpretable against the exact frozen content of X
- Reproducibility requires dataset freeze + evaluation run metadata (see Evaluation Run Metadata) + declared judge version
- Draft/unfrozen datasets MUST NOT be used to claim release reproducibility

#### Governance responsibilities

| Role (logical) | Responsibility |
|----------------|----------------|
| Dataset curator | Draft items, propose changelog, maintain lineage |
| Approver | Approve/reject for freeze; enforce review for gate-loosening changes |
| Evaluation architect | Schema fitness, tier placement, profile binding |
| Domain Pack owner | Domain label correctness |
| Release owner | Ensure Release profile pins approved frozen versions |

---

## 2. Metric Catalog (Canonical)

All metrics below are architectural obligations. Exact computational formulas are deferred to planning/implementation; definitions here are outcome-level and testable.

### Retrieval metrics

| Metric | Definition (architectural) | Primary subject |
|--------|----------------------------|-----------------|
| **Recall** | Fraction of relevant labeled items retrieved within the evaluated cutoff | Retrieval Engine (+ plan constraints) |
| **Precision** | Fraction of retrieved items that are relevant within the evaluated cutoff | Retrieval Engine |
| **MRR** | Reciprocal rank of the first relevant item | Retrieval Engine |
| **NDCG** | Graded ranking quality at a declared cutoff | Retrieval Engine |

### Planner metrics

| Metric | Definition (architectural) | Primary subject |
|--------|----------------------------|-----------------|
| **Plan Fidelity** | Agreement between produced plan signals and labeled expected planner outcomes (intent preservation, required constraints, forbidden re-parse) | Retrieval Planner |
| **Strategy Alignment** | Selected strategies are justified by Understood Query signals and capability rules (018-compatible) | Retrieval Planner |

### Answer quality metrics

| Metric | Definition (architectural) | Primary subject |
|--------|----------------------------|-----------------|
| **Faithfulness** | Factual claims in the answer are supported by cited / provided evidence (014-compatible) | Answer Generation |
| **Groundedness** | Claims are claim-level grounded to evidence identities (018-compatible; stricter continuity than coarse faithfulness) | Answer Generation |
| **Completeness** | Required answer facets / sub-questions are addressed (014-compatible) | Answer Generation (+ upstream evidence sufficiency) |

### Citation & safety metrics

| Metric | Definition (architectural) | Primary subject |
|--------|----------------------------|-----------------|
| **Citation Accuracy** | Citations resolve correctly and support the claims they are attached to; broken or mismatched citations fail | Answer Generation + Context citation chain |
| **Hallucination Rate** | Rate of answers/claims with unsupported or fabricated content (including fabricated entities/numbers) | Answer Generation (primary); may be diagnosed upstream |

### Operational metrics

| Metric | Definition (architectural) | Primary subject |
|--------|----------------------------|-----------------|
| **Latency** | End-to-end and stage-attributable time to produce an answer (or evaluation subject output) | Whole pipeline / stages |
| **Cost** | Attributed resource cost per evaluation item or request (model/token/compute accounting units declared per run) | Whole pipeline / stages |

### Metric honesty rules

- Missing labels ⇒ metric **N/A**, not zero
- `no_answer = true` ⇒ faithfulness / groundedness / completeness use no-answer correctness rules; do not auto-fail as hallucination unless labels require an answer
- Empty citation map ⇒ citation accuracy / faithfulness are **N/A** (or dedicated “ungrounded generation” failure if an answer was asserted as grounded)
- Coverage-style source checks remain available as retrieval/evidence diagnostics and MUST remain compatible with 014 coverage semantics when expected sources are labeled

---

## 2A. Metric Ownership

**Rule**: Every failed metric has **exactly one Primary Owner** for regression attribution. Supporting Stages provide diagnostic context only and MUST NOT split primary ownership. Primary Owners map to existing 016 production stage owners (or whole-pipeline operational attribution for Latency/Cost) — they do **not** create new production stages.

| Metric | Primary Owner | Supporting Stages | Blocking vs Diagnostic | Evaluation Scope |
|--------|---------------|-------------------|------------------------|------------------|
| **Recall** | Retrieval Engine | Retrieval Planner (constraints), Evidence (post-retrieval visibility) | **Blocking** when relevance labels exist in the active profile | Offline; online proxy optional |
| **Precision** | Retrieval Engine | Retrieval Planner | **Blocking** when relevance labels exist in the active profile | Offline; online proxy optional |
| **MRR** | Retrieval Engine | Retrieval Planner | **Blocking** in retrieval-focused / Release profiles when labeled; else Diagnostic | Offline; online proxy optional |
| **NDCG** | Retrieval Engine | Retrieval Planner | **Blocking** in retrieval-focused / Release profiles when labeled; else Diagnostic | Offline; online proxy optional |
| **Plan Fidelity** | Retrieval Planner | Query Understanding (Understood Query authority) | **Blocking** when planner labels exist in the active profile | Offline; online diagnostic optional |
| **Strategy Alignment** | Retrieval Planner | Query Understanding | **Blocking** when planner labels exist in the active profile; else Diagnostic | Offline; online diagnostic optional |
| **Faithfulness** | Answer Generation | Evidence, Context | **Blocking** | Offline primary; online proxy / shadow |
| **Groundedness** | Answer Generation | Evidence, Context | **Blocking** | Offline primary; online proxy / shadow |
| **Completeness** | Answer Generation | Evidence, Retrieval Engine | **Blocking** when facet labels exist | Offline primary; online proxy optional |
| **Citation Accuracy** | Answer Generation | Context Builder (citation chain), Evidence | **Blocking** | Offline primary; online proxy / shadow |
| **Hallucination Rate** | Answer Generation | Evidence, Context | **Blocking** | Offline primary; online proxy / monitoring |
| **Latency** | Whole Pipeline (operational attribution) | All production stages (stage tails are supporting diagnostics) | **Blocking** in Ops / Release / Production Monitoring profiles; Diagnostic in Smoke | Offline + online + monitoring |
| **Cost** | Whole Pipeline (operational attribution) | All production stages (stage cost shares are supporting diagnostics) | **Blocking** in Ops / Release / Production Monitoring profiles; Diagnostic in Smoke | Offline + online + monitoring |

**Attribution clarification**:

- If Planner constraints correctly exclude items, Engine MUST NOT be blamed for those exclusions as Recall misses when labels mark them out-of-scope — primary defect shifts to Planner only when constraints themselves are wrong (Plan Fidelity / Strategy Alignment).
- Completeness failures caused by missing upstream evidence still list Answer Generation as Primary Owner for the *metric*, with Error Taxonomy category indicating upstream contribution (see Error Taxonomy and Metric Dependency Model).
- Latency/Cost “Whole Pipeline” ownership is an **evaluation attribution sink** for composed runtime behavior; it does not invent a new 016 production sole owner.

---

## 2B. Metric Dependency Model

Architectural dependency (upstream → downstream effects). No formulas.

```
Query Understanding quality
        ↓
Planner quality (Plan Fidelity, Strategy Alignment)
        ↓
Retrieval Quality (Recall, Precision, MRR, NDCG)
        ↓
Evidence Quality (sufficiency / coverage diagnostics)
        ↓
Context Quality (citation chain readiness, budget/priority)
        ↓
Faithfulness
        ↓
Groundedness
        ↓
Completeness
        ↓
Citation Accuracy  ←── also depends on Context citation continuity
        ↓
Hallucination Rate (safety aggregate over unsupported / fabricated claims)

Latency & Cost  ←── cross-cutting over the entire chain
```

### Upstream failures

- Planner defects reshape candidate sets and can collapse Retrieval metrics even when Engine ranking is locally competent
- Retrieval defects starve Evidence and Context, lowering Faithfulness / Groundedness / Completeness ceilings
- Context citation-chain defects primarily surface as Citation Accuracy failures and can inflate Hallucination Rate when claims are citation-washed

### Downstream effects

- A retrieval miss often appears downstream as Completeness or Hallucination symptoms; architecture MUST still attempt root-cause attribution upstream when labels allow
- Improving Completeness without Faithfulness/Groundedness is not considered quality success under blocking profiles that include those metrics

### Root-cause attribution

1. Score all enabled metrics for the item
2. Apply Metric Ownership for each failed metric (single primary owner each)
3. Apply dependency order to mark **likely root cause** vs **downstream effect** when multiple metrics fail on one item
4. Reports MUST show both: primary owner per failed metric, and nominated root-cause stage when dependency analysis applies
5. Dependency analysis NEVER reassigns Primary Owner; it only annotates causal interpretation

---

## 2C. Judge Architecture

Evaluation assumes an abstract **Judge Layer** behind metric contracts.

### Judge types (interchangeable)

| Judge type | Role |
|------------|------|
| **Rule Judge** | Deterministic rule / label matching judgments |
| **LLM Judge** | Model-assisted judgments under the same metric semantics |
| **Human Judge** | Human adjudication for labels, audits, or escalation |
| **Hybrid Judge** | Composition of the above with declared precedence |

### Architectural requirements

- Metric identities and pass/fail semantics MUST remain stable regardless of judge implementation
- Runs MUST record which judge type(s) and judge version produced each scored metric (see Metric Confidence)
- Switching judges MUST NOT silently redefine Faithfulness, Groundedness, or other canonical metrics
- Judge implementation details, prompts, and models are out of scope; only the interchangeability contract is in scope
- Blocking gates MAY require a designated judge class per metric in a profile; that designation is architectural policy, not an implementation choice in this document

---

## 2D. Metric Confidence

Evaluation outputs MAY optionally expose confidence metadata without changing metric contracts:

| Field | Purpose |
|-------|---------|
| **confidence** | Optional certainty of the judgment for a metric on an item |
| **judge version** | Identity of the judge configuration that produced the score |
| **agreement** | Optional agreement signal when multiple judges contribute (Hybrid / multi-judge) |
| **evaluation provenance** | Trace of how the score was produced (inputs referenced, judge type, dataset item id, run id) |

**Purpose**: Support future multi-judge systems and audits without revising Evaluation Run or Item Result contracts. Absence of confidence fields MUST be valid; consumers treat missing confidence as unknown, not as failure.

---

## 3. Stage Evaluation Contracts

### 3.1 Retrieval evaluation

**Inputs (logical)**: Understood Query / plan constraints, retrieval candidates or ranked results, relevance labels  
**Outputs**: Recall, Precision, MRR, NDCG at declared cutoffs; missing-relevant and false-positive diagnostics  
**Obligations**:

- Cutoffs are declared in the run policy (e.g., @k family) and recorded in results
- Plan filters/constraints that correctly exclude items MUST NOT be scored as retrieval misses when labels mark them out-of-scope
- Results MUST be attributable to Engine vs Planner when failures are constraint vs ranking defects

### 3.2 Planner evaluation

**Inputs**: Understood Query, Retrieval Plan, optional planner labels  
**Outputs**: Plan Fidelity, Strategy Alignment; residual/unapplied constraint flags  
**Obligations**:

- Planner MUST NOT be credited for Engine execution quality
- Re-parse of raw user text contrary to Understood Query authority (018) is a planner fidelity failure when labeled

### 3.3 Answer evaluation

**Inputs**: Answer Result, Context / citation map, Evidence Pack (when available), golden facets / reference  
**Outputs**: Faithfulness, Groundedness, Completeness  
**Obligations**:

- Preserve 014 semantics for Faithfulness and Completeness
- Groundedness evaluates claim-level support continuity (018), not only coarse answer similarity
- Multi-part questions score completeness per facet

### 3.4 Citation evaluation

**Inputs**: Answer claims, citation attachments, Context citation chain  
**Outputs**: Citation Accuracy; lists of unresolved, mismatched, or unsupported citations  
**Obligations**:

- A correct citation identity that does not support the attached claim fails Citation Accuracy
- Citation continuity breaks (018 C5) are citation evaluation failures even if answer text “sounds right”

### 3.5 Hallucination detection

**Inputs**: Answer claims, evidence/citations, adversarial labels when present  
**Outputs**: Hallucination Rate; unsupported claim inventory  
**Obligations**:

- Distinguishes unsupported claim, fabricated entity/number, and citation-washed hallucination (claim cites irrelevant source)
- Complements — does not replace — inline production grounding guards; deeper detection remains evaluation/monitoring

### 3.6 Latency & cost evaluation

**Inputs**: Stage timings, token/resource accounting from Quality Trace / run telemetry  
**Outputs**: Latency distributions and Cost totals/averages per dataset slice  
**Obligations**:

- Report distribution summaries suitable for tail-aware gating (architecture requires a high-percentile view; exact statistic selection is planning detail)
- Cost units are declared per run; cross-run comparison requires same unit policy
- Quality-improving changes that blow cost/latency budgets are visible gate failures when policies require it

---

## 3A. Error Taxonomy

Canonical evaluation error categories standardize reporting, dashboards, and regression attribution. An Item Result MAY carry one primary error category and optional secondary categories.

| Category | Meaning | Typical primary metric owners |
|----------|---------|-------------------------------|
| **Retrieval Failure** | Relevant material not retrieved or ranking quality insufficient under labels | Retrieval Engine |
| **Planner Failure** | Plan signals, constraints, or strategy choices incorrect vs labels / Understood Query | Retrieval Planner |
| **Context Failure** | Context assembly / priority / compression / citation-chain readiness defects | Context Builder (supporting metrics); may surface via Citation Accuracy |
| **Citation Failure** | Missing, unresolved, or claim-mismatched citations | Answer Generation (Citation Accuracy) |
| **Grounding Failure** | Claims not grounded / not faithful to evidence | Answer Generation |
| **Generation Failure** | Answer content defects not primarily citation/grounding (including incomplete facets when evidence was sufficient) | Answer Generation |
| **Evaluation Failure** | Evaluation could not score validly (corrupt fixture, incompatible schema, judge unavailable for required metric) | Evaluation system (not a production stage owner) |
| **Infrastructure Failure** | Subject outputs or telemetry unavailable due to environmental failure | Operational / infra attribution (not a production RAG stage owner) |

**Rules**:

- Primary error category SHOULD align with Metric Ownership for the dominant failed blocking metric
- Evaluation Failure and Infrastructure Failure MUST never be mis-reported as production stage quality success or silent PASS under blocking profiles
- Taxonomy categories are for evaluation reporting; they do not create new production pipeline stages

---

## 4. Evaluation Pipeline

### Pipeline stages (architectural)

1. **Resolve run policy** — profile, mode, dataset tier(s), metric set, cutoffs, gate class, baseline / experiment role
2. **Load dataset version** — validate schema and freeze/compatibility; fail closed on corrupt or unfrozen Core Golden when profile requires freeze
3. **Obtain subject outputs** — offline replay / recorded snapshots / live shadow / canary / sampled production traces
4. **Score per item** — invoke applicable evaluators via Judge Layer; emit per-item metric vector, optional confidence, defect attribution, error taxonomy
5. **Aggregate** — dataset-level metrics, composite scores, slices
6. **Gate** — compare aggregates and critical item failures to profile-bound regression policy
7. **Persist & report** — store run with full metadata, emit machine-readable result + human summary; update trends; emit alerts when configured

### Defect attribution

Each item failure MUST include:

- Failed metric id(s)
- Primary owner (from Metric Ownership) — exactly one per failed metric
- Supporting stages (optional context)
- Primary error taxonomy category
- Optional dependency root-cause annotation
- Evidence pointers (missing source ids, unsupported spans, bad citation ids, rank of first relevant, etc.)
- Severity for gating (blocker vs warning)

### Evaluation Run Metadata

An Evaluation Run MUST be able to record the following for reproducibility (fields optional only when genuinely unavailable; blocking profiles SHOULD require the subset needed for their claims):

| Metadata | Purpose |
|----------|---------|
| **run id** | Stable identity |
| **commit** | Source revision under test |
| **branch** | Development line |
| **release** | Release identifier when applicable |
| **prompt version** | Prompt lineage affecting generation |
| **embedding version** | Embedding artifact/version identity |
| **reranker version** | Reranker artifact/version identity |
| **retriever version** | Retriever configuration/version identity |
| **planner version** | Planner configuration/version identity |
| **model version** | Generation model identity |
| **configuration fingerprint** | Aggregate config hash / fingerprint of relevant settings |
| **dataset version** | Frozen dataset identity |
| **profile** | Evaluation profile used |
| **experiment role** | Baseline / Candidate / Champion / Challenger / Shadow / Canary |
| **judge type(s) / version(s)** | Judge Layer provenance |
| **cost unit policy** | Declared Cost accounting units |
| **gate decision** | Pass / fail / skip with reasons |

---

## 4A. Evaluation Profiles

Reusable architectural profiles bind dataset tiers, metrics, gates, and expectations. Profiles define **configuration shape only** — not concrete numeric thresholds.

| Profile | Dataset tier(s) | Enabled metrics (architectural set) | Gate type | Runtime expectations | Cost expectations |
|---------|-----------------|-------------------------------------|-----------|----------------------|-------------------|
| **Smoke** | Tiny Core subset | Minimal: Faithfulness, Hallucination Rate, Latency (diagnostic Cost) | Advisory / break-glass sanity | Fastest offline path; fail closed only on Evaluation Failure | Cost recorded; not primary blocker |
| **PR** | Core Golden (frozen) | Retrieval (when labeled) + Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate; Latency diagnostic | **PR Core Gate** | Suitable for every merge-affecting change; deterministic offline | Cost recorded; blocker only if profile policy enables Cost |
| **Nightly** | Extended Golden + Adversarial / Probe | Full quality metric set applicable to labels; Latency + Cost | **Nightly Extended Gate** | Broader offline; may be longer-running than PR | Cost tracked vs prior nightly baseline |
| **Weekly** | Extended + Benchmark sample slices | Full quality + IR metrics on benchmark slices; Latency + Cost | Trend / soft gate (warnings → release attention) | Heavier offline; trend-oriented | Cost trend emphasis |
| **Release** | Frozen Core + Extended + designated Benchmark pins | All labeled metrics in catalog applicable to pinned sets; Latency + Cost blocking-capable | **Pre-release Benchmark Gate** + PR-class quality gates | Highest assurance offline before champion release | Cost must be comparable to champion baseline under same unit policy |
| **Shadow** | Online Sample Labels + optional probe overlays | Proxies for Faithfulness / Groundedness / Citation / Hallucination; Latency + Cost; IR proxies when labels exist | **Online Drift** advisory (policy may promote) | Asynchronous vs user traffic; 015-compatible inputs | Live cost observation |
| **Production Monitoring** | Telemetry windows + sparse Online Sample Labels | Health proxies + Latency + Cost; quality proxies per Drift Taxonomy | **Ops Gate** + **Online Drift Gate** | Continuous / rolling; never request-path owner | Continuous cost surveillance |

**Profile rules**:

- A run MUST declare exactly one primary profile (additional informational suites allowed as secondary reports)
- Profiles MUST NOT invent parallel production paths
- Moving a metric from Diagnostic to Blocking is a profile/governance change, not a metric redefinition

---

## 5. Regression Testing & Gates

### Gate classes

| Gate class | When | Effect |
|------------|------|--------|
| **PR Core Gate** | PR profile | Must satisfy Core Golden blocking metrics |
| **Nightly Extended Gate** | Nightly profile | Extended Golden + adversarial probes |
| **Pre-release Benchmark Gate** | Release profile | Benchmark corpus / pinned sets vs champion baseline |
| **Online Drift Gate** | Shadow / Production Monitoring | Alerts; optional promotion to release blocker under incident policy |
| **Ops Gate** | Production Monitoring / Release ops checks | Latency / cost SLO-style policy breaches |

### Regression rules

- Baseline is an explicit prior run id or champion experiment reference
- A regression is a metric drop beyond configured absolute or relative delta, or a newly failing critical item
- Improving one metric MUST NOT hide a blocker regression on Hallucination Rate, Faithfulness, Groundedness, or Citation Accuracy when those are in the gate set
- Flaky items MUST be quarantined via dataset metadata rather than silently ignored by raising thresholds
- Gate decisions consume Metric Ownership and Error Taxonomy for actionable failure summaries

### Relationship of gates to alerts

- **Gates** are decision points bound to profiles (pass/fail/skip for merge, release, or policy)
- **Alerts** are monitoring notifications that may precede, accompany, or follow gates; alerts do not replace offline gate authority for merge by default

---

## 5A. Experiment Architecture

Evaluation comparison model for architecture-level experiment roles (no deployment mechanics):

| Role | Meaning |
|------|---------|
| **Baseline** | Reference run against which deltas are computed |
| **Candidate** | Proposed change under evaluation |
| **Champion** | Current accepted production-quality reference for a release line |
| **Challenger** | Contender seeking to replace champion based on evaluation gates |
| **Shadow** | Non-user-visible evaluation against live-like inputs |
| **Canary** | Limited exposure observation role for evaluation comparison (traffic mechanics out of scope) |

**Obligations**:

- Comparisons MUST pin compatible dataset versions (or explicitly declare controlled dataset evolution)
- Champion replacement is an evaluation/governance outcome (gates + review), not an automatic side effect of a single metric win
- Shadow/Canary evaluation MUST remain compatible with 015 sole user-visible path rules
- Experiment role is recorded on Evaluation Run Metadata

---

## 5B. Composite Quality Scores

Aggregated quality indicators exist for executive reporting and trend views. **No formulas are defined here** — only architectural purpose.

| Composite score | Architectural purpose |
|-----------------|----------------------|
| **Overall Quality Score** | Single executive indicator summarizing multi-metric quality posture for a run or window |
| **Retrieval Quality Score** | Rolls up retrieval metrics (Recall/Precision/MRR/NDCG as available) for retrieval owners |
| **Planning Quality Score** | Rolls up Plan Fidelity / Strategy Alignment for planner owners |
| **Generation Quality Score** | Rolls up Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate |
| **Production Health Score** | Rolls up live quality proxies with Latency and Cost posture for operators |

**Rules**:

- Composites are **derived views**; they MUST NOT replace per-metric gates for blocking decisions unless a profile explicitly names a composite as advisory-only or (rarely) as a named gate input
- Composites MUST preserve drill-down to underlying metrics, owners, and error taxonomy
- Missing constituent metrics yield partial composites with explicit coverage declaration — not silent full scores

---

## 6. CI Integration (Contract)

CI integration is a **contract**, not a product choice.

**Required behaviors**:

- Machine-readable evaluation report (structured artifact) per run
- Non-zero failure signal when PR Core Gate fails
- Report includes: run id, dataset version, configuration fingerprint and related Evaluation Run Metadata, per-metric aggregates, composite scores (if produced), failed item ids, error taxonomy summary, gate decision, experiment role
- Ability to compare against a stored baseline / champion run
- Evaluation MUST be invokable without serving user traffic
- Secrets and raw PII from production samples MUST NOT be required for Core Golden CI

---

## 7. Offline vs Online Benchmarks

### Offline benchmarks

- Use versioned Benchmark Corpus (+ Extended Golden / adversarial)
- Optimized for reproducibility and attribution
- Primary authority for merge/release quality decisions when bound by profile

### Online benchmarks

- Consume shadow / dual-run / canary outputs and/or privacy-safe production samples
- Measure live drift categories (see Drift Taxonomy), Latency, Cost, and sampled quality proxies
- MUST NOT block every user request; operate asynchronously
- Online results are advisory to offline gates unless a documented incident policy promotes them to release blockers

### Benchmark Governance

| Concern | Architectural rule |
|---------|-------------------|
| **Lifecycle** | Draft → Approved → Frozen → (Optionally Retired / Superseded), parallel to dataset lifecycle |
| **Immutability** | Frozen benchmark versions do not mutate in place; corrections create new versions |
| **Reproducibility** | A benchmark score claim MUST cite frozen benchmark version + run metadata + judge version |
| **Versioning** | Explicit benchmark version identity distinct from ad hoc scrapes |
| **Comparability** | Cross-release comparisons require same frozen benchmark version OR an explicit version-evolution bridge in the report |
| **Tagging** | Benchmarks carry tags (domain, language, intent mix, adversarial, IR-only, answer-only, etc.) for slice-compatible selection |
| **Evolution process** | Propose → review impact on champion baselines → approve → freeze → update Release profile pins → changelog → communicate incomparability windows |

---

## 8. Production Monitoring

Monitoring views (information architecture — not vendor UI):

| View | Questions answered |
|------|--------------------|
| **Quality Health** | Faithfulness / groundedness / hallucination / citation trends |
| **Retrieval Health** | Online proxies for recall/precision drift; empty-result and low-evidence rates |
| **Planner Health** | Strategy mix, degradation rate, residual filter rate |
| **Ops Health** | Latency, cost per request, error/no-answer rates |
| **Gate Status** | Last Core/Extended/Benchmark gate outcomes and open regressions |
| **Defect Hotspots** | Top attributed owners, error taxonomy categories, and failing slices |
| **Drift Board** | Active drift categories and severity |
| **Experiment Board** | Champion / challenger / shadow / canary evaluation posture |

Monitoring MUST reuse Quality Trace / Quality Context fields from 018 where available rather than inventing a second telemetry model.

### Drift Taxonomy

Online Drift is categorized architecturally:

| Drift category | Meaning |
|----------------|---------|
| **Data Drift** | Indexed / corpus content distribution shifts affecting answerability |
| **Query Drift** | Live query mix shifts vs offline datasets (intent, complexity, language) |
| **Retrieval Drift** | Live retrieval outcome distribution shifts (hit rates, empty results) |
| **Ranking Drift** | Ordering quality proxies shift vs offline IR posture |
| **Citation Drift** | Citation resolution / mismatch proxies degrade |
| **Answer Drift** | Answer quality proxies (faithfulness/groundedness/completeness/hallucination) shift |
| **Latency Drift** | Latency distributions worsen vs baseline window |
| **Cost Drift** | Cost per request / unit policy worsens vs baseline window |

**Relationship to offline regression**:

- Offline regression gates remain primary for merge/release quality authority
- Drift categories explain *live* divergence and may trigger alerts, shadow emphasis, or dataset evolution
- Persistent drift SHOULD feed Dataset Evolution (new labels, probes, benchmark tags) — not silent threshold relaxation

### Alert Architecture

| Alert category | Meaning | Typical relation to gates |
|----------------|---------|---------------------------|
| **Threshold Alert** | A monitored signal crossed a policy threshold | May mirror Ops / Drift gate inputs |
| **Regression Alert** | Offline or scheduled run regressed vs baseline/champion | Often emitted alongside gate FAIL |
| **Trend Alert** | Multi-window adverse trend without single-point breach | Early warning; usually advisory |
| **Drift Alert** | One or more Drift Taxonomy categories elevated | Online Drift Gate companion |
| **Cost Alert** | Cost posture breach or sharp increase | Ops Gate companion |
| **Latency Alert** | Latency posture breach or sharp increase | Ops Gate companion |

Alerts notify; gates decide. An alert without a gate decision MUST NOT be treated as merge PASS.

---

## 9. Reporting & Dashboards

### Report types

1. **Item report** — single question/item metric vector + ownership + error taxonomy + optional confidence
2. **Run report** — aggregates, composites, gate decision, baseline/champion diff, metadata fingerprint
3. **Trend report** — metric and composite time series across runs / releases
4. **Slice report** — metrics broken down by standard slicing dimensions
5. **Executive summary** — Overall / Production Health composites, hallucination rate, latency/cost posture, top regressions and drifts

Dashboards are the operational presentation of these report types. Concrete layout/tooling is out of scope; the architecture requires that the underlying run store can satisfy these views.

### Slice Architecture

Standard slicing dimensions (architecture-level; an item/run MAY carry any subset as tags):

| Dimension | Purpose |
|-----------|---------|
| **domain** | Domain Pack / business domain mix |
| **language** | Query/answer language |
| **intent** | Understood / labeled intent class |
| **query complexity** | Complexity band (e.g., simple vs multi-part / multi-hop labeled bands) |
| **retrieval strategy** | Strategies used / expected |
| **planner strategy** | Planner strategy choices under evaluation |
| **document type** | Source document type mix |
| **tenant** | Tenant / isolation slice when applicable |
| **context size** | Context budget / size band |
| **answer length** | Answer length band |
| **dataset tier** | Core / Extended / Adversarial / Benchmark / Online Sample |

**Rules**:

- Slice reports MUST not invent metrics; they re-aggregate canonical metrics
- Blocking gates MAY optionally require no blocker regressions on designated critical slices
- Slices support Dataset Evolution prioritization when drift concentrates in a dimension

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Block a Quality Regression on Merge (Priority: P1)

A pipeline engineer changes retrieval ranking. Before merge, CI runs the **PR** evaluation profile on frozen Core Golden. Retrieval and answer metrics are scored; a Recall and Completeness drop beyond gate policy fails the build with a machine-readable report listing failed items, primary owners, and error taxonomy.

**Why this priority**: Prevents silent quality loss — the primary purpose of the evaluation framework.

**Independent Test**: Using a tiny Core Golden fixture and two recorded output snapshots (good vs degraded retrieval), the orchestrator passes the good snapshot and fails the degraded one with non-zero gate signal and Retrieval Engine as primary owner for Recall.

**Acceptance Scenarios**:

1. **Given** a frozen Core Golden dataset version and a baseline-passing snapshot, **When** the offline evaluation run executes under the PR profile, **Then** the run report shows aggregate pass and gate decision PASS.
2. **Given** the same dataset where required relevant chunks are removed from retrieval results, **When** evaluation re-runs, **Then** Recall and dependent Completeness/Faithfulness signals degrade measurably, gate decision is FAIL, Recall primary owner is Retrieval Engine, and dependency annotation may mark Completeness as downstream effect.
3. **Given** a corrupt Core Golden file, **When** evaluation starts, **Then** the run fails closed as Evaluation Failure with a descriptive error and does not emit a false PASS.

---

### User Story 2 - Score Retrieval Ranking Quality (Priority: P1)

A retrieval owner wants IR metrics — Recall, Precision, MRR, NDCG — against graded relevance labels for a benchmark slice, independent of answer generation.

**Why this priority**: Many answer failures are retrieval failures; retrieval must be evaluable without waiting on generation.

**Independent Test**: A three-query labeled set with known rankings produces expected ordering of NDCG/MRR between a good ranking and a shuffled ranking; primary owner remains Retrieval Engine.

**Acceptance Scenarios**:

1. **Given** graded relevance labels and a ranked candidate list, **When** the Retrieval Evaluator scores the item, **Then** Recall, Precision, MRR, and NDCG at declared cutoffs are present (or N/A only if labels missing).
2. **Given** identical labels and a worse ranking of the same candidates, **When** scored, **Then** MRR and/or NDCG decrease while attribution remains with Retrieval Engine.

---

### User Story 3 - Detect Hallucinations and Bad Citations (Priority: P1)

A quality engineer runs adversarial probes containing fabricated entities and mismatched citations. The framework flags Hallucination Rate and Citation Accuracy failures with unsupported claim and citation diagnostics under Grounding / Citation failure categories.

**Why this priority**: Hallucinations and citation-washed errors are the highest-severity trust failures.

**Independent Test**: One answer with a fabricated drug strength and one with a citation pointing to an irrelevant chunk both fail the appropriate metrics; a fully grounded cited answer passes; judge type may vary without changing metric identities.

**Acceptance Scenarios**:

1. **Given** an answer containing a numeric/entity claim absent from cited evidence, **When** hallucination and faithfulness evaluation run, **Then** Hallucination Rate contribution and Faithfulness reflect failure, unsupported spans are listed, and primary owner is Answer Generation.
2. **Given** a claim cited to a resolved but irrelevant source, **When** Citation Accuracy is scored, **Then** the item fails Citation Accuracy even if the citation id exists.
3. **Given** a correct no-answer when evidence is missing (labeled), **When** scored, **Then** the item is not counted as a hallucination failure.

---

### User Story 4 - Evaluate Planner Decisions (Priority: P2)

A planner owner validates that plans preserve Understood Query intent and select aligned strategies on a labeled planner slice.

**Why this priority**: Bad plans poison retrieval metrics; planner defects must be separable from Engine ranking defects.

**Independent Test**: A labeled item expecting a filter constraint fails Plan Fidelity when the plan omits it; Engine metrics are marked not applicable for that defect class; primary owner is Retrieval Planner.

**Acceptance Scenarios**:

1. **Given** planner labels requiring a constraint, **When** the plan omits it, **Then** Plan Fidelity fails and attribution points to Retrieval Planner under Planner Failure.
2. **Given** a plan that re-interprets raw text contrary to Understood Query labels, **When** scored, **Then** Plan Fidelity / Strategy Alignment fails per policy.

---

### User Story 5 - Compare Offline Benchmark Runs Across Releases (Priority: P2)

A team lead compares challenger release candidate R2 to champion baseline R1 on a frozen Benchmark Corpus version. The trend report shows metric deltas, composite scores, and regressed items by owner and slice.

**Why this priority**: Release readiness needs broader evidence than the small Core Golden set.

**Independent Test**: Two persisted run reports with a single metric regression produce a diff that flags only that metric/items and preserves experiment roles Champion vs Challenger.

**Acceptance Scenarios**:

1. **Given** two complete offline benchmark runs on the same frozen benchmark version, **When** a diff is requested, **Then** per-metric deltas, composite deltas, and regressed item ids are listed.
2. **Given** no baseline/champion, **When** a run completes, **Then** it is stored as a baseline/champion candidate and the report states baseline absence without failing solely for that reason.

---

### User Story 6 - Observe Production Drift and Ops Health (Priority: P3)

An operator reviews dashboards for Answer Drift, Citation Drift, Latency Drift, and Cost Drift. Latency and Cost alerts fire when posture breaches policy; Drift alerts fire when quality proxies breach rolling thresholds; offline gate status remains visible beside live drift.

**Why this priority**: Protects production after merge; complements offline gates.

**Independent Test**: Synthetic monitor fixtures with breached latency posture and elevated unsupported-claim proxy produce Latency/Cost and Drift alerts without invoking the user-facing answer path.

**Acceptance Scenarios**:

1. **Given** rolling telemetry exceeding latency policy, **When** Ops Gate / Latency Alert evaluation runs, **Then** Latency Drift / Latency Alert is marked with time window and slice.
2. **Given** elevated unsupported-claim proxy over the configured window, **When** Drift Gate evaluation runs, **Then** Answer Drift is reported with linkage to recent offline gate status when available.

---

### Edge Cases

- Relevance labels missing for an item ⇒ retrieval metrics N/A; answer metrics may still score if answer labels exist
- Expected source IDs deleted from the index ⇒ coverage/recall-style checks count miss + warning; suite continues
- Empty citation map with non-empty assertive answer ⇒ groundedness/citation fail or dedicated ungrounded-generation failure; not silent pass
- Shadow path unavailable ⇒ Shadow profile degrades to SKIP with explicit status (never silent PASS)
- Cost accounting incomplete for a stage ⇒ Cost metric partial with declared missing components; gate policy decides fail-open vs fail-closed
- Dual-run disagreement (015) ⇒ evaluation may score both sides for shadow/challenger reports; user-visible path remains sole production owner
- Judge disagreement in Hybrid mode ⇒ agreement metadata recorded; profile policy decides blocker vs escalate-to-human
- Unfrozen dataset used with Release profile ⇒ fail closed (compatibility / freeze violation)
- Multiple metrics fail on one item ⇒ each metric keeps its single primary owner; dependency model annotates root cause separately

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The framework MUST provide an evaluation architecture covering offline golden/regression, offline benchmarks, online shadow evaluation, and production monitoring — without owning the production answer path.

- **FR-002**: The framework MUST define versioned dataset tiers: Core Golden, Extended Golden, Adversarial/Probe, Benchmark Corpus, and Online Sample Labels.

- **FR-003**: The framework MUST support retrieval evaluation producing Recall, Precision, MRR, and NDCG at declared cutoffs when relevance labels exist.

- **FR-004**: The framework MUST support planner evaluation producing Plan Fidelity and Strategy Alignment when planner labels exist.

- **FR-005**: The framework MUST support answer evaluation producing Faithfulness, Groundedness, and Completeness, preserving 014 semantics for Faithfulness and Completeness.

- **FR-006**: The framework MUST support citation evaluation producing Citation Accuracy, including unresolved and claim-mismatched citations.

- **FR-007**: The framework MUST support hallucination detection producing Hallucination Rate with unsupported/fabricated claim diagnostics.

- **FR-008**: The framework MUST treat Latency and Cost as first-class metrics alongside quality metrics, with run-declared cost units and latency aggregates suitable for gating.

- **FR-009**: The evaluation pipeline MUST resolve run policy/profile, load dataset version, obtain subject outputs, score items via the Judge Layer, aggregate (including composites and slices), apply gates, persist results with Evaluation Run Metadata, and support alerts.

- **FR-010**: Every failed metric MUST include exactly one primary owner from Metric Ownership, optional supporting stages, and a primary Error Taxonomy category.

- **FR-011**: The framework MUST define regression gate classes: PR Core, Nightly Extended, Pre-release Benchmark, Online Drift, and Ops — bound to Evaluation Profiles.

- **FR-012**: CI integration MUST emit a structured run report and a failing signal when PR Core Gate fails.

- **FR-013**: Runs MUST record Evaluation Run Metadata sufficient for reproducibility claims of the active profile, including dataset version, configuration fingerprint, gate decision, and experiment role when applicable.

- **FR-014**: Baseline/champion diffing MUST identify metric regressions and newly failing critical items between comparable runs.

- **FR-015**: Metric honesty rules MUST apply: N/A for missing labels; special handling for no-answer; no false zero when citations are absent.

- **FR-016**: Online/shadow evaluation MUST be asynchronous relative to user traffic and MUST NOT create a second production owner for retrieval or answer.

- **FR-017**: Production monitoring MUST expose Quality, Retrieval, Planner, Ops, Gate Status, Defect Hotspot, Drift Board, and Experiment Board views as information requirements.

- **FR-018**: Reporting MUST support item, run, trend, slice, and executive summary report types backed by persisted runs, including standard Slice Architecture dimensions.

- **FR-019**: Domain-specific expected answers/sources/labels MUST enter only via datasets or Domain Packs — not via hard-coded evaluation rules.

- **FR-020**: On disagreement between 018 stage heuristic diagnostics and 019 gate outcomes for release decisions, 019 gate outcomes MUST take precedence.

- **FR-021**: The framework MUST remain compatible with Quality Context / Quality Trace (018) as preferred telemetry/input enrichment for monitoring and offline alignment.

- **FR-022**: Evaluation architecture artifacts for this feature MUST NOT include implementation code; planning/implementation occurs in later phases.

- **FR-023**: The framework MUST define Metric Ownership for all canonical metrics with Primary Owner, Supporting Stages, Blocking vs Diagnostic posture, and Evaluation Scope.

- **FR-024**: The framework MUST define a Metric Dependency Model that distinguishes upstream failures, downstream effects, and root-cause annotation without reassigning Primary Owner.

- **FR-025**: The framework MUST define Evaluation Profiles: Smoke, PR, Nightly, Weekly, Release, Shadow, and Production Monitoring — each specifying dataset tiers, enabled metric sets, gate type, and runtime/cost expectation classes without concrete thresholds.

- **FR-026**: Dataset Governance MUST include lifecycle, approval, freeze, retirement, compatibility, lineage, changelog, and reproducibility guarantees with stated responsibilities.

- **FR-027**: The Judge Layer MUST support Rule, LLM, Human, and Hybrid judge types as interchangeable producers of metric judgments without changing metric semantics.

- **FR-028**: Item/metric outputs MAY include optional confidence, judge version, agreement, and evaluation provenance without requiring them for contract validity.

- **FR-029**: Benchmark Governance MUST include lifecycle, immutability, reproducibility, versioning, comparability, tagging, and an evolution process.

- **FR-030**: The framework MUST define the Error Taxonomy categories: Retrieval, Planner, Context, Citation, Grounding, Generation, Evaluation, and Infrastructure Failure.

- **FR-031**: The framework MUST define Drift Taxonomy categories: Data, Query, Retrieval, Ranking, Citation, Answer, Latency, and Cost Drift — and their relationship to offline regression authority.

- **FR-032**: The framework MUST support Experiment Architecture roles: Baseline, Candidate, Champion, Challenger, Shadow, and Canary.

- **FR-033**: The framework MUST define Composite Quality Scores (Overall, Retrieval, Planning, Generation, Production Health) as derived architectural indicators without mandating formulas.

- **FR-034**: Monitoring MUST define Alert categories: Threshold, Regression, Trend, Drift, Cost, and Latency — and clarify that alerts notify while gates decide.

- **FR-035**: Future Evaluation Extensions listed in this specification MUST be treated as extension points only; they MUST NOT expand current production ownership or require implementation in this feature’s architecture phase.

### Key Entities

- **Evaluation Dataset**: Versioned collection of evaluation items across a tier, under Dataset Governance.
- **Evaluation Item**: Single scored unit (query + labels + thresholds + slice tags).
- **Run Policy / Evaluation Profile**: Profile-bound mode, tiers, metrics enabled, gate class, runtime/cost expectation class, baseline/experiment role.
- **Evaluation Run**: Persisted execution with Evaluation Run Metadata, aggregates, item results, composites, gate decision.
- **Item Result**: Per-item metric vector, N/A flags, optional confidence/provenance, diagnostics, primary owners, error taxonomy, dependency annotations, pass/fail.
- **Metric Definition**: Canonical metric id, ownership row, required labels, honesty rules, blocking/diagnostic posture by profile.
- **Judge**: Abstract interchangeable judgment producer (Rule / LLM / Human / Hybrid) with version identity.
- **Regression Gate**: Named gate class with profile binding and enforcement context (CI, nightly, release, online).
- **Baseline Diff / Experiment Compare**: Comparison across experiment roles and runs.
- **Monitoring View Model**: Logical dashboard requirements over rolling telemetry, drift taxonomy, alerts, and recent gates.
- **Composite Quality Score**: Derived aggregate indicator with drill-down to constituents.
- **Cost Unit Policy**: Declared accounting units for a run’s Cost metric comparability.
- **Benchmark**: Governed, versioned corpus with immutability and comparability rules.
- **Alert**: Categorized monitoring notification related to, but distinct from, gates.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Evaluation logic MUST respect Clean Architecture boundaries (application evaluation contracts vs infrastructure persistence/telemetry adapters).
- **NFR-002**: Evaluation I/O MUST be async-friendly; public contracts MUST be typed and structured.
- **NFR-003**: Judges/evaluators MUST be replaceable behind stable interfaces without changing gate metric semantics.
- **NFR-004**: RAG citation obligations remain: citation evaluation assumes production answers expose traceable citations when retrieval was used.
- **NFR-005**: Prompt/version/config fingerprints relevant to answer quality MUST be recordable on runs when available.
- **NFR-006**: Unit/contract tests (when implemented later) MUST cover pass and fail paths per metric family; this architecture phase requires only that such coverage be feasible.
- **NFR-007**: Structured logging/telemetry for runs MUST include run id, dataset version, gate decision, primary owners, error taxonomy, and correlation-friendly identifiers — never secrets or unnecessary PII.
- **NFR-008**: Secrets MUST NOT be required in Core Golden offline CI datasets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reviewers can validate, from architecture artifacts alone, that offline, online-shadow, and production-monitoring modes are distinct and that none owns the user-facing answer path.

- **SC-002**: For a Core Golden set of at least 10 items with retrieval and answer labels, an offline PR-profile run produces a complete run report including Recall, Precision, MRR, NDCG (where labeled), Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate, Latency, and Cost — or explicit N/A with reason per missing label — within a single orchestrated evaluation pass.

- **SC-003**: A deliberately degraded retrieval ranking on a labeled slice causes measurable decline in at least one of MRR or NDCG, fails the configured retrieval gate, and attributes Recall/MRR/NDCG primary ownership to Retrieval Engine.

- **SC-004**: A fabricated entity/number in an otherwise well-formed answer causes Hallucination Rate and Faithfulness (and Groundedness when claim-level labels exist) to fail for that item with unsupported-claim diagnostics and Answer Generation as primary owner.

- **SC-005**: A mismatched citation (resolved id, irrelevant support) fails Citation Accuracy even when Faithfulness heuristics might partially pass on overlapping tokens.

- **SC-006**: Planner label violations fail Plan Fidelity / Strategy Alignment with attribution to Retrieval Planner under Planner Failure, without marking Engine ranking as the primary defect.

- **SC-007**: PR Core Gate produces a machine-readable fail signal suitable for CI when aggregate or critical-item thresholds are breached; profile-bound Extended/Benchmark/Online/Ops gates are defined with distinct enforcement contexts.

- **SC-008**: Baseline/champion diff between two runs on the same frozen dataset/benchmark version surfaces at least one injected Completeness or Recall regression and does not flag unchanged items as regressed.

- **SC-009**: Production monitoring information architecture includes Quality, Retrieval, Planner, Ops, Gate Status, Defect Hotspot, Drift Board, and Experiment Board views; operators can state which offline gate last passed/failed alongside active drift categories and alert categories.

- **SC-010**: Domain swap test: replacing dataset artifacts with another domain’s labels requires no change to evaluation architecture rules for metrics/gates/profiles to remain meaningful.

- **SC-011**: Stakeholders confirm that 014 Faithfulness/Completeness semantics remain valid, 018 stage diagnostics remain non-authoritative for release vs 019 gates, 016 sole-owner constraints are not violated, and Metric Ownership does not create new production stages.

- **SC-012**: Reviewers can trace Dataset → Evaluation → Reports → Gates → Release → Shadow → Production Monitoring → Dataset Evolution as one lifecycle without identifying a new production RAG stage.

- **SC-013**: For any failed canonical metric in a sample run report, exactly one Primary Owner is present, consistent with the Metric Ownership table.

- **SC-014**: A run record can include commit/branch/release and component version/fingerprint fields listed under Evaluation Run Metadata sufficient to explain reproducibility of a Release-profile claim.

## Assumptions

- This feature is architecture-only; implementation, formulas, judge internals, and concrete thresholds happen in later plan/task phases.
- Feature 019 becomes the evaluation architecture authority; 014 remains the semantic seed for coverage/faithfulness/completeness and is extended rather than discarded.
- Evaluation never runs as a mandatory synchronous step on the user-facing request path.
- Core Golden remains small enough for PR gating; Benchmark Corpus may be too large for every PR and is gated at Nightly/Weekly/Release by default.
- Online labels are sparse; online gates use proxies and sampling, with offline golden remaining primary merge authority.
- Cost is measured in declared accounting units; exact unit catalog is a planning detail.
- Latency gates use distribution summaries suitable for tail latency, not only averages.
- Human review remains required for Core Golden threshold loosening and for dataset freeze of blocking tiers.
- Shadow/dual-run infrastructure from 015 may supply online evaluation inputs when enabled; if unavailable, Shadow profile reports SKIP rather than PASS.
- LLM Judge and Hybrid Judge are architectural options; architecture does not require a specific judge type for v1 semantics.
- “Whole Pipeline (operational attribution)” for Latency/Cost is an evaluation attribution concept, not a new 016 production sole owner.
- Ingest quality evaluation (chunking/OCR) may be added later as a dataset subject without changing production ingest ownership.
- Future Evaluation Extensions are compatibility placeholders only until separately specified.

---

## Future Evaluation Extensions

The following are **future-compatible extension points**. They are not in current delivery scope, MUST NOT add production stages, and MUST NOT alter existing 016 ownership boundaries. When specified later, they SHOULD reuse Metric Ownership, Judge Layer, Profiles, Dataset/Benchmark Governance, Error Taxonomy, Drift Taxonomy, and Experiment Architecture.

| Extension | Intent |
|-----------|--------|
| **Multimodal Evaluation** | Evaluate quality when inputs/evidence include non-text modalities |
| **Agent Evaluation** | Evaluate multi-step agent behavior built on RAG capabilities |
| **Conversation Evaluation** | Evaluate multi-turn conversational quality and continuity |
| **Tool Calling Evaluation** | Evaluate correctness and necessity of tool/function invocation |
| **Long Context Evaluation** | Evaluate quality under large context budgets and long documents |
| **Multi-hop Evaluation** | Evaluate reasoning chains requiring multiple evidence hops |
| **Safety Evaluation** | Evaluate safety/policy posture beyond hallucination metrics |
| **Reasoning Evaluation** | Evaluate structured reasoning quality distinct from surface fluency |

**Extension rule**: New evaluation subjects plug into datasets, judges, metrics (with ownership), profiles, and reports — they do not create parallel production answer/retrieval owners.
)

# Data Model: RAG Evaluation Framework

**Feature**: 019-rag-evaluation-framework | **Date**: 2026-07-18

Logical entities for evaluation architecture. No persistence schema, wire format, or ORM mapping is prescribed.

---

## Entity Overview

| Entity | Purpose |
|--------|---------|
| EvaluationDataset | Versioned labeled collection under governance |
| EvaluationItem | Single scored unit inside a dataset |
| Benchmark | Governed corpus for offline benchmarking |
| EvaluationProfile | Reusable binding of tiers, metrics, gates, expectation classes |
| RunPolicy | Concrete policy instance for a run (usually from a profile) |
| Judge | Abstract judgment producer with type + version |
| EvaluationRun | Persisted orchestrated scoring execution |
| ItemResult | Per-item metric outcomes + attribution |
| MetricDefinition | Canonical metric identity + ownership row |
| MetricScore | One metric outcome on one item (optional confidence) |
| CompositeQualityScore | Derived rollup indicator |
| RegressionGate | Named decision gate bound to a profile |
| BaselineDiff | Comparison between runs / experiment roles |
| ExperimentRef | Role assignment (Baseline…Canary) |
| MonitoringWindow | Rolling observation window for drift/alerts |
| Alert | Categorized monitoring notification |
| DatasetVersionLineage | Predecessor/successor + changelog linkage |

---

## EvaluationDataset

| Field (logical) | Meaning |
|-----------------|---------|
| dataset_id | Stable identity across versions |
| version | Immutable version identity when frozen |
| tier | Core Golden / Extended Golden / Adversarial / Benchmark / Online Sample |
| lifecycle_state | Draft / In Review / Approved / Frozen / Retired / Superseded |
| schema_compat | Compatibility marker vs evaluator contract generation |
| lineage | Predecessor version reference |
| changelog_ref | Human-readable change summary for this version |
| approval | Approver identity + timestamp + rationale (when approved/frozen) |

### State transitions

```text
Draft → In Review → Approved → Frozen → Retired
                              ↘ Superseded (by newer Frozen)
```

- **Frozen**: content identity immutable
- Blocking profiles (PR/Release) require Frozen for bound datasets
- Corrections create a new version; do not mutate Frozen in place

---

## EvaluationItem

| Field (logical) | Meaning |
|-----------------|---------|
| item_id | Stable within dataset version |
| query | User query text |
| understood_query_labels | Optional parse/intent labels |
| relevance_labels | Graded/binary labels for IR metrics |
| planner_labels | Expected plan/strategy/constraint labels |
| expected_source_ids | Optional coverage-style expectations |
| expected_answer_facets | Completeness facets |
| reference_answer | Optional |
| citation_expectations | Claim→source expectations |
| no_answer_label | Expected abstention posture |
| match_mode | Exact / semantic / graded relevance declaration |
| slice_tags | Standard slice dimensions (see Slice tags) |
| metric_threshold_overrides | Optional; architecture allows, values non-normative |

### Slice tags (standard dimensions)

domain, language, intent, query_complexity, retrieval_strategy, planner_strategy, document_type, tenant, context_size, answer_length, dataset_tier

---

## Benchmark

| Field (logical) | Meaning |
|-----------------|---------|
| benchmark_id | Stable identity |
| version | Frozen version identity |
| lifecycle_state | Same governance phases as datasets |
| tags | domain/language/intent-mix/adversarial/IR-only/answer-only/… |
| pinned_dataset_refs | Dataset versions composing the benchmark |
| immutability | Frozen ⇒ no in-place mutation |
| comparability_notes | When cross-version compare is/isn’t valid |

---

## EvaluationProfile

| Field (logical) | Meaning |
|-----------------|---------|
| profile_id | Smoke / PR / Nightly / Weekly / Release / Shadow / Production Monitoring |
| dataset_tiers | Allowed/required tiers |
| enabled_metrics | Canonical metric set for the profile |
| gate_type | Gate class binding |
| runtime_expectation_class | Qualitative runtime envelope (e.g., fast / extended / continuous) |
| cost_expectation_class | Qualitative cost posture (record / trend / blocking-capable) |
| freeze_required | Whether bound datasets/benchmarks must be Frozen |

Profiles define configuration *shape*, not numeric thresholds.

---

## RunPolicy

Resolved policy for one EvaluationRun: profile_id, dataset/benchmark pins, enabled metrics, cutoffs declaration, baseline/champion references, experiment role, judge requirements, gate class.

---

## Judge

| Field (logical) | Meaning |
|-----------------|---------|
| judge_type | Rule / LLM / Human / Hybrid |
| judge_version | Configuration/version identity |
| precedence_notes | For Hybrid: which judgment wins on conflict (architectural policy, not implementation) |

Judges produce MetricScores; they do not redefine MetricDefinition semantics.

---

## MetricDefinition

| Field (logical) | Meaning |
|-----------------|---------|
| metric_id | Recall, Precision, MRR, NDCG, Plan Fidelity, Strategy Alignment, Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate, Latency, Cost |
| primary_owner | Exactly one attribution owner |
| supporting_stages | Optional diagnostic supporters |
| blocking_vs_diagnostic | Default posture; profiles may narrow |
| evaluation_scope | Offline / online proxy / monitoring |
| required_labels | What must exist or else N/A |
| honesty_rules | N/A and no-answer handling |

---

## MetricScore

| Field (logical) | Meaning |
|-----------------|---------|
| metric_id | Canonical id |
| value | Score or distribution summary reference |
| status | Pass / Fail / N/A / Skip |
| confidence | Optional |
| judge_version | Optional/required by profile |
| agreement | Optional multi-judge agreement |
| evaluation_provenance | Optional input/judgment trace references |
| primary_owner | Copied/resolved from Metric Ownership |
| error_category | Primary Error Taxonomy category when failed |

---

## ItemResult

| Field (logical) | Meaning |
|-----------------|---------|
| item_id | Subject item |
| metric_scores | List of MetricScore |
| primary_error_category | Dominant Error Taxonomy category |
| secondary_error_categories | Optional |
| root_cause_annotation | Dependency-model interpretation (does not override primary owners) |
| supporting_diagnostics | Missing sources, unsupported spans, bad citations, ranks, etc. |
| passed | Item-level gate contribution |

### Error Taxonomy (canonical categories)

Retrieval Failure · Planner Failure · Context Failure · Citation Failure · Grounding Failure · Generation Failure · Evaluation Failure · Infrastructure Failure

---

## EvaluationRun

| Field (logical) | Meaning |
|-----------------|---------|
| run_id | Stable identity |
| profile_id | Primary profile |
| experiment_role | Baseline / Candidate / Champion / Challenger / Shadow / Canary |
| dataset_version(s) | Pins |
| benchmark_version | Optional pin |
| gate_decision | Pass / Fail / Skip + reasons |
| aggregates | Per-metric aggregates |
| composites | Optional CompositeQualityScore set |
| item_results | Collection of ItemResult |
| created_at | Run timestamp |

### Evaluation Run Metadata (reproducibility)

commit · branch · release · prompt_version · embedding_version · reranker_version · retriever_version · planner_version · model_version · configuration_fingerprint · judge type(s)/version(s) · cost_unit_policy

Blocking profiles SHOULD require the metadata subset needed for their reproducibility claims.

---

## CompositeQualityScore

| Field (logical) | Meaning |
|-----------------|---------|
| composite_id | Overall / Retrieval / Planning / Generation / Production Health |
| coverage_declaration | Which constituents were present vs missing |
| drilldown_refs | Links to underlying metrics/owners |

No formula is defined at architecture level.

---

## RegressionGate

| Field (logical) | Meaning |
|-----------------|---------|
| gate_class | PR Core / Nightly Extended / Pre-release Benchmark / Online Drift / Ops |
| profile_binding | Which profile(s) invoke it |
| decision | Pass / Fail / Skip |
| failed_item_ids | Blockers |
| owner_summary | Aggregated primary owners |
| error_taxonomy_summary | Aggregated categories |

---

## BaselineDiff / ExperimentRef

**ExperimentRef**: run_id + role (Baseline, Candidate, Champion, Challenger, Shadow, Canary)

**BaselineDiff**: compares two runs on compatible dataset/benchmark versions; lists metric deltas, composite deltas, newly failing critical items, unchanged items (must not false-flag).

---

## MonitoringWindow / Alert

**MonitoringWindow**: time/slice window over live telemetry + sparse online labels; produces drift category statuses.

**Drift categories**: Data · Query · Retrieval · Ranking · Citation · Answer · Latency · Cost

**Alert**:

| Field (logical) | Meaning |
|-----------------|---------|
| alert_category | Threshold / Regression / Trend / Drift / Cost / Latency |
| severity | Architectural severity band (values non-normative) |
| related_gate | Optional companion gate |
| slice_scope | Optional slice dimensions |
| evidence_refs | Links to runs/windows |

Alerts notify; gates decide.

---

## Relationships to 016 Ownership

| Evaluation primary owner | Maps to existing production concern |
|--------------------------|-------------------------------------|
| Retrieval Planner | retrieval_planning |
| Retrieval Engine | retrieval_execution |
| Answer Generation | answer generation owner |
| Context Builder (supporting) | context owner |
| Evidence (supporting) | evidence owner |
| Whole Pipeline (ops attribution) | evaluation attribution only — **not** a new 016 sole owner |
| Evaluation system | non-production path |

---

## Relationships (summary)

```text
EvaluationDataset 1──* EvaluationItem
Benchmark *──* EvaluationDataset (pins)
EvaluationProfile ──► RunPolicy ──► EvaluationRun
EvaluationRun *──* ItemResult *──* MetricScore ──► MetricDefinition
EvaluationRun *──* CompositeQualityScore
EvaluationRun ──► RegressionGate decision
EvaluationRun ──► ExperimentRef
Judge ──► MetricScore
MonitoringWindow ──► Alert
EvaluationDataset ──► DatasetVersionLineage
```
)

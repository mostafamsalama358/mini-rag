# Contract: Evaluation Pipeline, Profiles & Gates

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative orchestration, profile bindings, gates, CI signal, and run metadata.

---

## Purpose

Define how evaluation executes as a non-production path and how decisions are produced.

---

## Pipeline stages (architectural)

1. Resolve run policy (profile, pins, metrics, experiment role, judges)
2. Load dataset/benchmark versions (freeze/compat checks)
3. Obtain subject outputs (replay / snapshot / shadow / canary / sampled traces)
4. Score items via Judge Layer (metrics, optional confidence, taxonomy, ownership)
5. Aggregate (metrics, composites, slices)
6. Gate (profile-bound decision)
7. Persist & report (metadata, diffs, alerts when configured)

---

## Modes

| Mode | Authority posture |
|------|-------------------|
| Offline golden/regression | Primary for merge (PR profile) |
| Offline benchmark | Primary for broader release assurance |
| Online shadow | Advisory by default; policy may promote |
| Production monitoring | Ops/drift authority for live posture; not merge primary |

Evaluation MUST NOT be a mandatory synchronous step on the user-facing answer path.

---

## Profiles (configuration shape only)

| Profile | Dataset tiers | Gate type | Runtime class | Cost class |
|---------|---------------|-----------|---------------|------------|
| Smoke | Tiny Core subset | Advisory sanity | Fastest offline | Record |
| PR | Frozen Core Golden | PR Core Gate | Merge-suitable offline | Record (blocker only if policy enables) |
| Nightly | Extended + Adversarial | Nightly Extended Gate | Broader offline | Trend vs prior nightly |
| Weekly | Extended + Benchmark slices | Soft/trend gate | Heavier offline | Trend emphasis |
| Release | Frozen Core + Extended + pinned Benchmarks | Pre-release Benchmark + quality gates | Highest offline assurance | Comparable to champion |
| Shadow | Online Sample (+ probes) | Online Drift (advisory default) | Async vs user traffic | Live observation |
| Production Monitoring | Telemetry windows + sparse labels | Ops + Online Drift | Continuous/rolling | Continuous surveillance |

**Rules**:

- Exactly one primary profile per run (secondary informational suites allowed)
- Profiles MUST NOT invent parallel production paths
- No concrete numeric thresholds are defined in this contract

---

## Gate classes

PR Core · Nightly Extended · Pre-release Benchmark · Online Drift · Ops

**Regression rules**:

1. Baseline/champion reference is explicit
2. Safety metrics (Hallucination Rate, Faithfulness, Groundedness, Citation Accuracy) cannot be hidden by unrelated metric gains when in the gate set
3. Flaky items are quarantined via dataset metadata, not silent threshold hikes
4. Gate summaries include primary owners and error taxonomy

---

## CI contract

Machine-readable run report + failing signal on PR Core Gate failure.

Report MUST be able to include: run id, dataset/benchmark versions, configuration fingerprint and related run metadata, aggregates, composites (if any), failed item ids, error taxonomy summary, gate decision, experiment role.

Core Golden CI MUST NOT require production secrets or raw PII.

---

## Evaluation Run Metadata

Runs MUST be able to record:

commit · branch · release · prompt version · embedding version · reranker version · retriever version · planner version · model version · configuration fingerprint · dataset/benchmark versions · profile · experiment role · judge type(s)/version(s) · cost unit policy · gate decision

---

## Acceptance

Contract review fails if:

- Evaluation is designed as a mandatory user-request-path stage
- PR profile can pass without frozen Core pins
- CI has no machine-readable fail signal for PR Core Gate
- Run metadata cannot support Release reproducibility claims
)

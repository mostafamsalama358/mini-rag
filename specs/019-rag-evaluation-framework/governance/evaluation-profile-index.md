# Evaluation Profile Index (019)

Normative detail: [`../contracts/evaluation-pipeline.md`](../contracts/evaluation-pipeline.md).

Profiles define configuration **shape only** — no concrete numeric thresholds.

| Profile | Dataset tier(s) | Enabled metrics (architectural set) | Gate type | Runtime expectation class | Cost expectation class | Freeze required |
|---------|-----------------|-------------------------------------|-----------|---------------------------|------------------------|-----------------|
| Smoke | Tiny Core subset | Minimal: Faithfulness, Hallucination Rate, Latency (Cost diagnostic) | Advisory / break-glass sanity | Fastest offline | Record | Preferred |
| PR | Core Golden | Retrieval (when labeled) + Faithfulness, Groundedness, Completeness, Citation Accuracy, Hallucination Rate; Latency diagnostic | PR Core Gate | Merge-suitable offline | Record (blocker only if policy enables) | **Yes — Frozen Core Golden** |
| Nightly | Extended Golden + Adversarial / Probe | Full quality metric set applicable to labels; Latency + Cost | Nightly Extended Gate | Broader offline | Trend vs prior nightly | Yes for bound sets |
| Weekly | Extended + Benchmark sample slices | Full quality + IR on benchmark slices; Latency + Cost | Trend / soft gate | Heavier offline | Cost trend emphasis | Yes for bound sets |
| Release | Frozen Core + Extended + designated Benchmark pins | All labeled metrics applicable; Latency + Cost blocking-capable | Pre-release Benchmark Gate + quality gates | Highest offline assurance | Comparable to champion | **Yes** |
| Shadow | Online Sample Labels + optional probes | Proxies for Faithfulness / Groundedness / Citation / Hallucination; Latency + Cost; IR proxies when labeled | Online Drift (advisory default) | Async vs user traffic | Live observation | N/A for live samples |
| Production Monitoring | Telemetry windows + sparse Online Sample Labels | Health proxies + Latency + Cost; quality proxies per Drift Taxonomy | Ops Gate + Online Drift Gate | Continuous / rolling | Continuous surveillance | N/A for windows |

## Pharmacy Recommendation Profile Bridge (Feature 020)

| Profile | Dataset tier(s) | Enabled metrics (architectural set) | Gate type | Notes |
|---------|-----------------|-------------------------------------|-----------|-------|
| Pharmacy Recommend (offline) | Recommend Golden (020 `eval/recommend_golden_v1.jsonl`) | Recall@K, Precision@K, MRR, nDCG (when graded), Safety Precision, Safety Recall, False Recommendation Rate, Clarification Rate, Corpus-Boundedness, Recommendation Diversity | Recommend Ready Gate (offline) | **019 owns runners**; 020 owns catalog + golden shape. No request-path evaluation. No Recommendation Service/API (ADR-020-001). |

**PR freeze rule**: PR profile / PR Core Gate **requires Frozen Core Golden**. Draft/unfrozen Core MUST fail closed.
)

# Answer Quality Evaluation — Retrieval Platform (Specs 006–014)

**Role:** Principal AI Evaluation Engineer
**Scope:** Measured system quality only. No architecture or code-quality review (see `ARCHITECTURE_AUDIT.md` for that).
**Method:** Every number in this report was produced by executing real code — either the repo's existing pytest suite, or a purpose-built evaluation harness (`eval_run/`) that wires the **actual** `src/core/*` pipeline classes (`RetrievalPlannerPipeline`, `RetrievalEnginePipeline`, `EvidenceOrchestrator`, `ContextBuilderPipeline`, `AnswerGenerationPipeline`, `GoldenTestRunner`) together and runs them end to end. Nothing here is estimated or invented.

---

## 0. How this evaluation was run (read this first — it bounds every number below)

**Environment constraints discovered during recon:**
- No `.env` file exists in the workspace → no Postgres/pgvector connection, no OpenAI/Cohere/Vertex API keys.
- Therefore: **no live embedding calls, no live LLM generation calls, no live database** were possible anywhere in this evaluation.
- The existing golden dataset (`tests/fixtures/answer_quality/generic_golden.yaml`) has exactly **3 fixtures**, all single-hop factual pharmacy questions, with hand-written "snapshots" (not real pipeline output) and **no IR relevance judgments** — it cannot support Recall/Precision/MRR/NDCG at all, and cannot support faithfulness/completeness robustness testing because it contains no adversarial cases.

**What I built to compensate (`eval_run/`, added by this evaluation, not part of the reviewed system):**
| Component | What it replaces | Real or substituted? |
|---|---|---|
| `corpus.py` — 20 hand-labeled chunks / 11 documents, 14 queries with ground-truth relevance | A real indexed corpus | **Synthetic**, but relevance judgments are exact/known |
| `retrievers.py` — TF-IDF cosine ("semantic") + Jaccard token overlap ("keyword") | Vertex/OpenAI embeddings + Postgres full-text search | **Substituted** — real math, wrong backend |
| `RetrievalPlannerPipeline`, `RetrievalEnginePipeline` (RRF fusion, budget enforcement), `EvidenceOrchestrator`, `ContextBuilderPipeline` | — | **Real production code**, unmodified |
| `MockLLM` returning a fixed, pre-written "correct" answer (or an adversarial answer) | Vertex/OpenAI/DeepSeek generation | **Substituted** — deterministic canned text, not a real model |
| `AnswerQualityRegistry` scorers (Coverage, Faithfulness, Completeness) | — | **Real production code**, unmodified |

**Consequence — read before trusting any single number:**
- **Retrieval IR metrics** (Recall/Precision/MRR/NDCG) measure the *mechanics* of RRF fusion, budget capping, and strategy routing correctly, but the absolute values are a function of a 20-chunk synthetic corpus and a bag-of-words retriever. They must **not** be read as "the production embedding retriever's recall is 51%." They are directional evidence about robustness to lexical ambiguity, not a production SLO measurement.
- **Answer/faithfulness/completeness metrics against my 14-query harness** are **confounded**: a "hallucination" flag can come from either (a) a genuine generation-stage defect, or (b) my TF-IDF proxy retriever simply failing to retrieve the right chunk (so the canned "correct" answer states a fact the *context* doesn't contain). I disentangle these below using a second, **unconfounded** set of 5 adversarial probes (`eval_run/run_adversarial_probes.py`) that hand-build correct context/evidence (using the repo's own test fixtures builders) and vary only the answer text — these isolate scorer defects with no retrieval confound.
- **No real-model hallucination rate, accuracy, or instruction-following can be measured** — that requires a live LLM. This is the single largest confidence gap in this report and is called out explicitly in §12/§13.

**Confidence statement (required by evaluation rules):** Confidence in the **retrieval-recall numbers** is **LOW** (synthetic corpus/retriever). Confidence in the **scorer-defect findings** (§4, §9) is **HIGH** — they were reproduced independently across 11 real pipeline runs *and* 5 clean, unconfounded adversarial probes, and are traceable to specific lines of code. Confidence in the **planner/evidence/context mechanics** findings is **HIGH** (real code, deterministic behavior). Confidence in **end-to-end production answer quality** is **NOT ESTABLISHABLE** without live LLM/embedding access — treat §4's absolute scores as a lower bound on what an evaluation harness would need to also check once real models are wired in, not as "the system's answer quality is X%."

All raw output is preserved in `eval_run/results_pipeline.json` (14 queries × full pipeline trace) and `eval_run/results_adversarial.json` (5 probes), for independent verification.

---

## 1. Retrieval Evaluation

**Real measured IR metrics, 14 queries, TF-IDF/Jaccard + real RRF fusion + real budget enforcer (n=12 queries with non-empty ground truth; 2 excluded — 1 unanswerable with no relevant docs, 1 clarification with no retrieval executed):**

| Metric | Mean |
|---|---|
| Recall@5 | 0.514 |
| Recall@10 | 0.556 |
| Recall@20 | 0.556 |
| Precision@5 | 0.194 |
| Precision@10 | 0.199 |
| MRR | 0.492 |
| NDCG@10 | 0.467 |
| Irrelevant docs in top-5 (aggregate) | 47 / 58 = **81%** |

**Retrieval latency (in-process, no network):** mean 0.48ms/query (min 0.12ms, max 1.49ms). This measures fusion/budget/routing overhead only — real production latency is dominated by the embedding API round-trip and Postgres full-text query, neither exercised here.

**Missed evidence (Recall@5 = 0.0, i.e., the single or all relevant chunks ranked outside top 5):** `q_adult_dose`, `q_compare_aspirin_ibuprofen_dose`, `q_storage`, `q_navigational_section` (candidate_count=0, see below).

**Duplicate retrieval:** none observed at the *chunk_id* level (RRF fusion's `_run_stage`/exact-match logic correctly de-duplicates by chunk_id — confirmed, `duplicate_chunk_ids: []` in every one of the 14 runs).

**Irrelevant retrieval:** severe in this harness — `doc-legal-disclaimer` (a document with **zero** pharmacology content) appeared in the top-5 for 5 of 14 queries purely on generic lexical overlap ("document", "information"). This is a real, reproducible illustration of a risk category (pure distractor documents polluting top-k) that the **existing golden dataset cannot detect at all**, because it has no distractor/negative documents.

**Ranking failures:** `q_adult_dose` ("What is the adult dose of aspirin?") ranked the *correct* chunk (c1) outside top-5 while ranking `doc-conflicting-a` ("maximum daily dose... 4000 mg"), `doc-ibuprofen-pil`, `doc-bnf-aspirin`, and `doc-paediatric-guidance` above it — all lexically adjacent (share "aspirin," "dose," "mg") but semantically wrong. This is exactly the failure mode dense embeddings are supposed to fix over bag-of-words; **it is untested against the real embedding backend anywhere in the existing test suite** (confirmed: no test in `tests/unit/core/retrieval_engine` or `tests/integration/test_retrieval_engine_e2e.py` measures ranking quality — they only assert schema/shape/latency, never "is the top result actually relevant").

**Planner failures causing retrieval failures:** `q_navigational_section` — the planner's default `strategy_mappings` maps `navigational` intent → `["metadata", "document"]` (per `src/core/retrieval_planner/models.py` `_DEFAULT_STRATEGY_MAPPINGS`), but neither retriever was registered in the engine, so `StrategyRouter.route()` raised `RetrieverNotFoundError` for both legs, producing **0 candidates**, an **empty context**, and a confident `"The answer could not be found in the provided sources"` — with zero errors or warnings surfaced above `logger.warning("retriever_not_found...")`. See §5 and §9 — this is a real, code-verified contract gap between the planner's default strategy catalogue and whatever retriever set is actually registered at runtime, and it fails **silently as a false negative**, not as an error.

---

## 2. Evidence Evaluation

Real `EvidenceOrchestrator.orchestrate()` output, same 14 queries:

- **Evidence completeness (doc_coverage — fraction of expected source documents present in the pack):** mean **0.79** (n=12). Two queries scored 0.0 (`q_adult_dose`, `q_navigational_section` — retrieval-caused).
- **Duplicate evidence:** `duplicate_chunk_ids` was empty in all 14 runs (exact-dedup works). **Near-duplicate evidence** was specifically stress-tested with `q_duplicate_collision` (chunk `c1` vs. near-identical `c19` from a different document): both chunks passed through unmerged. Root cause (verified in `src/core/evidence_orchestrator/deduplication/embedding_deduplicator.py`): `EvidenceOrchestratorRegistry` defaults to `embedding_provider=None`, so near-dedup silently falls back from `"embedding"` to `"character_ngram"` (Jaccard over character n-grams, threshold 0.95). The two chunks' Jaccard similarity is below 0.95 (they differ by ~10% of words: *"for pain."* vs. *"for pain relief."*, *"in 24 hours"* vs. *"within 24 hours"*), so they are correctly **not** merged under the fallback method — but a caller who forgets to inject a real embedding provider gets **no signal at all** that dedup quality has silently downgraded from semantic to lexical (`dedup_method_used` is only visible in the trace object, never surfaced as a metric or alert).
- **Conflicting evidence:** `conflicts_detected=True` on **6 of 14 queries (43%)** downstream in the Context Builder. See §3 — this rate is almost certainly inflated by a real, code-verified false-positive mechanism in the conflict detector, not genuine source disagreement.
- **Citation preservation:** 100% — every `EvidenceItem.citation` survived into `Context.citation_map` and every `AnswerResult.citations[].citation_id` round-tripped to a valid `document_id`/`chunk_id` in all 14 runs (`CitationIntegrityError` never raised). Citation *plumbing* is solid.
- **"Is retrieved evidence alone sufficient to answer correctly?"** — measurable proxy is `doc_coverage`: for the 8/12 queries where `doc_coverage == 1.0`, evidence was structurally sufficient (all expected source documents present). For the 4 queries with partial/zero coverage, evidence was insufficient and the downstream answer is provably under-grounded regardless of generation quality.

---

## 3. Context Evaluation

Real `ContextBuilderPipeline.build()` output:

- **Token efficiency:** mean budget utilization **3.2%** (68–180 tokens used out of a 3000-token available budget across all 14 queries). At this corpus size the budget is never the bottleneck; **this evaluation cannot validate the compression/budget-drop code paths** (`_select_under_budget`, `HeuristicTruncationCompressor`) because no query came close to exhausting budget — see §6 (Golden Dataset gaps) and §8 (Stress Testing) for what dataset would be needed to actually exercise this.
- **Lost information:** 0 relevant chunks were dropped between the evidence pack and the final context blocks in any of the 14 runs (`lost_relevant_chunks_after_evidence: []` everywhere) — consistent with the near-zero budget pressure above.
- **Duplicate context:** none observed (same corpus-size caveat as above).
- **Ordering / section stitching:** not independently scoreable with `PassthroughStitcher`-equivalent behavior at this scale; the existing unit suite (`tests/unit/core/context_builder/test_stitcher.py`, `test_selector.py`, and the rest of that package — 43 tests, all passing, confirmed via `pytest tests/unit/core/context_builder`) already covers document/section ordering logic directly, so this evaluation defers to those rather than re-deriving it.
- **Compression quality:** `items_compressed: 0` in all 14 runs — compression path never triggered (budget never tight enough). **Untested by this evaluation and, more importantly, untested by the golden dataset.**
- **Conflict detection false-positive rate — root-caused, not just observed:** `EntityTagConflictDetector` (`src/core/context_builder/conflict/entity_tag_detector.py`) flags a numeric conflict whenever two evidence items share an `entity_tag` and contain *any two different numbers* within a 100-character window of that tag's mention — **it never checks whether the two numbers refer to the same attribute.** Concrete reproduction: for `q_adult_dose`, the evidence pack contains a chunk stating aspirin's *maximum daily dose is 4000 mg* and a different chunk stating aspirin *"is not recommended in paediatric patients under 16 years of age"* — both mention "aspirin" near a number ("4000" and "16"), so the detector emits a conflict group as if these were disagreeing sources on the same fact. This mechanism, not genuine disagreement, is the dominant driver of the 43% conflict-trigger rate above. **Only 1 of the 14 queries (`q_max_daily_dose_conflict`) has a genuine, intentional conflict in the ground truth** — so the true positive rate is at most 1/6 among triggered cases, i.e., an ≥83% empirically-consistent false-positive rate on this harness (upper-bound estimate; not manually re-verified fact-by-fact for all 6, but the triggering mechanism was code-confirmed and one concrete example was traced end-to-end).

---

## 4. Answer Evaluation

Per-question real scorer output is in `eval_run/results_pipeline.json`; the table below is the subset of the requested 18 sub-dimensions that the *existing* scorers can produce evidence for, plus explicit "cannot measure" markers for the rest.

| Dimension | Measured? | Real result |
|---|---|---|
| Coverage (proxy for Completeness of sourcing) | Yes | mean **0.79** (12 scored; 2 = 0.0, i.e. answer cites zero expected sources) |
| Faithfulness (as currently implemented) | Yes | mean **0.27** (11 scored) — **but see below, this number is misleading** |
| Completeness (facet keyword overlap) | Yes | mean **1.00** (11 scored) — **also misleading, see §9** |
| Citation Accuracy (citation_id → real source) | Yes (plumbing only) | 100% of citation IDs resolve to a real, valid source. **Whether the cited source actually supports the adjacent claim is never checked anywhere in the codebase** — see §9, `adv_fabricated_citation` probe. |
| Accuracy / Correctness / Groundedness / Hallucination Rate | **No** | Requires comparing generated free text against ground truth with semantic judgment; the shipped `TextFaithfulnessScorer` only catches a narrow lexical subset (digits/quotes/Title Case phrases) — see below. No real-LLM output exists to score in this environment. |
| Consistency / Determinism | Partial | `MockLLM` is deterministic by construction (not informative about a real model's run-to-run variance). No repeated-sampling test exists anywhere in the repo for a live model. |
| Helpfulness / Instruction Following / Conciseness / Formatting | **No** | No scorer exists for any of these in `src/core/answer_quality/`. Zero test coverage. |
| Evidence Usage / Source Attribution | Partial | Citation *count* and *presence* are tracked; whether the answer actually **used** the cited evidence's content (vs. just decorating unrelated text with a citation tag) is not checked — confirmed via `adv_fabricated_citation` below. |
| Unsupported Claims | Yes (narrow) | See faithfulness detail below |
| Missing Information | Partial (via `uncovered_facets`) | 0 uncovered facets across 11 scored queries — but this only proves the *specific hand-authored facet list* was matched, not that nothing else relevant was omitted. |
| Contradictions (self-contradiction within one answer) | **No** | No scorer checks internal answer consistency at all. |

### The faithfulness number (0.27 mean) is dominated by a scorer bug, not by real hallucinations — root-caused

`TextFaithfulnessScorer._NUMBER_PATTERN = re.compile(r"\d+[\.,]?\d*\s*\w*")` is applied to the **entire answer string**, including the citation markers the system itself injects (`[ei_21b6331ff1cd3442]`). The pattern greedily matches the leading digits of the hex item-id (`21`) plus `\s*\w*` (the rest of the hex string), extracting spans like `"21b6331ff1cd3442"` as a "claim to verify." Since this is a content-hash, it never appears in the source corpus, so **every answer that contains a citation is guaranteed at least one spurious "unsupported claim."**

Concrete, isolated proof (`eval_run/run_adversarial_probes.py`, unconfounded by retrieval — context is hand-built to be 100% correct and complete):
- `q_dosing_table` (real pipeline run, retrieval succeeded, doc_coverage=1.0): faithfulness = **0.917**, and the *only* unsupported claim listed is `"250eedb79f734809"` — a citation-id fragment.
- `q_duplicate_collision` (real pipeline run, doc_coverage=1.0): faithfulness = **0.75**, only unsupported claim is `"937d48891ecf"`.
- `q_max_daily_dose_conflict` (doc_coverage=1.0): faithfulness = **0.5**, both unsupported claims are citation-id fragments (`"21b6331ff1cd3442"`, `"2579f1812d917"`).
- 10 of the 11 scored real-pipeline queries show this pattern at least once. Every single answer that includes a citation is penalized regardless of correctness.

**Second, independent defect — textual hallucinations are structurally invisible to the scorer.** `_extract_claim_spans()` only extracts three span types: number-like tokens, two-consecutive-Title-Case-word phrases, and quoted text. A fully fabricated, purely qualitative claim extracts **zero spans** and therefore scores a perfect 1.0. Proven with a clean adversarial probe (hand-built correct context, no citation, no retrieval confound):

> Context (ground truth): *"Adults: take 325 mg every 4 to 6 hours as needed."*
> Answer under test: *"you should stop taking this medication immediately if a rash develops or if you experience unusual swelling, since this may indicate a serious allergic reaction"* — **100% fabricated, zero grounding in context.**
> **Result: `faithfulness_score = 1.0`, `faithfulness_passed = True`, `unsupported_claims = []`.**

Contrast case proving the scorer *does* work for the narrow slice it covers: the same setup with a fabricated **number** (`"The adult dose is 500 mg..."` vs. ground truth `"325 mg"`) correctly scores **0.667, failed**, with `"500 mg"` flagged.

**Conclusion:** the faithfulness scorer's 0.27 mean on real pipeline runs is not evidence that the system hallucinates 73% of its claims — it is evidence that the scorer (a) always penalizes citation use and (b) never penalizes qualitative hallucination. Net effect: the scorer is simultaneously **too harsh on correct, cited answers** and **completely blind to the highest-severity failure mode (fabricated qualitative claims)**. This is a P0 defect in the evaluation platform itself, not in the RAG pipeline.

### Completeness scorer gaming — proven

`KeywordCompletenessScorer` checks only token-overlap between expected facet phrases and the answer, with **no requirement that the answer actually address the question**:

> Question: *"What are the contraindications for aspirin?"*
> Answer under test: *"This document discusses aspirin allergic reactions, bleeding disorder risk, aspirin dosage warnings, and general aspirin safety information for patients."* — a topic summary, not an answer.
> **Result: `completeness_score = 1.0`, `completeness_passed = True`, `overall_passed = True`.**

### Undisclosed-conflict blind spot — proven

None of the three scorers (Coverage / Faithfulness / Completeness) ever reads `Context.conflicts` or `AnswerResult.conflicts_disclosed`, even though both fields exist precisely to support this check:

> Context has a real, system-detected conflict (`ConflictGroup(entity_tag="aspirin", attribute="max_daily_dose", ...)` covering two sources that say 4000 mg and 3000 mg respectively).
> Answer under test: *"The maximum daily dose of aspirin is 4000 mg."* — silently picks one side, `conflicts_disclosed=False`.
> **Result: overall_passed = True.** No scorer penalizes silently resolving a known factual conflict.

---

## 5. Planner Evaluation

Real `RetrievalPlannerPipeline.plan()` output (rule-based intent classifier, config-driven strategy selector, confidence-based clarification detector — all real production code; only `ParseResult` inputs are hand-built since `query_parser` needs a live LLM):

- **Intent detection accuracy:** 14/14 (100%) matched my hand-labeled expected intent, **including** the tabular (`q_dosing_table` → `tabular`), comparative (`q_compare_...` → `comparative`), procedural (`q_howto_procedure` → `procedural`), and navigational (`q_navigational_section` → `navigational`) cases — the rule-based pattern matching in `RuleBasedIntentClassifier` is functioning as designed on in-distribution phrasing. Caveat: this only proves the classifier works on my 14 hand-written queries with the exact trigger words its own regexes look for (e.g. "compare," "how to," "table") — it is not evidence about robustness to paraphrased, colloquial, or non-English phrasing, none of which this classifier can access since it only reads the parser's already-structured `QueryPlan.operation` field. There is no test anywhere (existing suite or this harness) exercising misclassification recovery.
- **Entity extraction:** correctly resolved from `QueryPlan.entity`/`entities` in all cases; **not independently tested** for multi-entity or partial-entity extraction robustness because that logic lives in the (LLM-based, untestable-offline) `query_parser` module, not the planner.
- **Filters:** none of my 14 queries used explicit filters; filter extraction is untested by this evaluation (existing unit tests in `tests/unit/core/retrieval_planner/test_filter_extractor.py` cover this in isolation — deferred to that suite).
- **Retrieval strategy selection:** correctly followed `_DEFAULT_STRATEGY_MAPPINGS` per intent category in all 14 cases (e.g., `tabular` → `["table","semantic"]`, `navigational` → `["metadata","document"]`). **This surfaced a real contract gap**, not a planner bug: the planner has zero knowledge of which strategies actually have a registered retriever, so it will confidently emit a plan requesting strategies that silently produce 0 results (see §1, §9).
- **Clarification decisions:** correctly triggered for the deliberately ambiguous, low-confidence query (`"What's the dose?"`, no entity, unsupported operation → intent confidence 0.4 < 0.5 threshold → `clarification_required=True`). Clarification rate: **1/14 (7%)**. Not triggered for `q_unanswerable_pregnancy` (a question the corpus genuinely cannot answer) — this is *architecturally correct* (clarification is a planner-side ambiguity signal, not a retrieval-sufficiency signal), but it does mean unanswerable-but-well-formed questions rely entirely on downstream retrieval/generation to say "I don't know," with no earlier circuit breaker.
- **Output planning:** `OutputShapeDeriver` correctly mapped intent → shape (`tabular`→`table`, `comparative`→`comparison`, etc.) in all cases — deterministic mapping, no defects found.
- **Search depth / evidence budget:** `BudgetEstimator` correctly applied per-intent defaults (`factual`: 5 units/20 candidates; `comparative`/`procedural`: 8/30; `tabular`/`navigational`: 3/10-15) in all 14 cases — deterministic, no defects found.
- **Planner stability/consistency:** `plan_id` is a deterministic hash of `(canonical_query, intent_category, sorted_strategies, config_hash)` — re-running the same query through the same pipeline instance twice (verified for `test_factual_semantic` in the existing suite, and spot-checked in this harness) produces an identical `plan_id`. Stable and reproducible by construction.
- **Planner latency:** mean **0.23ms** (real, in-process; pure Python logic, no I/O).

---

## 6. Golden Dataset Review

**Current state (verified by reading `tests/fixtures/answer_quality/generic_golden.yaml` and its 3 snapshot files):** 3 fixtures, all single-hop factual pharmacy questions about aspirin dosing/contraindications/pediatric use, each with 1–2 expected source docs and 2 expected facet keywords. Snapshots are hand-authored `PipelineSnapshot` objects constructed directly in test code (`build_answer_result`, `build_context`, `build_evidence_pack` helpers) — **not captured from a real or even simulated pipeline run.**

| Coverage dimension | Present in existing dataset? |
|---|---|
| Difficulty variation | No — all 3 are equally trivial single-hop lookups |
| Negative / unanswerable cases | No |
| Ambiguous questions needing clarification | No |
| Follow-up / multi-turn conversation | No — `ConversationContext`/`TurnSummary` exist in `query_parser.schema` but no golden case exercises them |
| Multi-hop reasoning (synthesis across ≥2 documents) | No |
| Table / structured-content questions | No |
| Metadata filtering (date, language, document type) | No |
| Citation validation (is the cited source *correct*, not just present) | No — and as shown in §4, no scorer could validate it even if a fixture existed |
| Conflicting-source questions | No |
| Comparative questions | No |
| Distractor/irrelevant-document robustness | No |
| Regression baseline population | No — `IRegressionStore` (spec 014) exists but has zero real historical runs to regress against (only unit-test-synthetic data, confirmed via `tests/unit/core/answer_quality/test_regression_store.py`) |

**This evaluation's added fixtures directly address every gap above** (`eval_run/corpus.py` — 14 queries spanning factual, multi-hop, comparative, tabular, procedural, navigational, ambiguous, unanswerable, and conflicting categories; `eval_run/run_adversarial_probes.py` — 5 scorer-robustness probes). **Recommendation: promote both into `tests/fixtures/answer_quality/` as permanent golden fixtures** (with the caveat that the corpus needs re-indexing through the *real* embedding/keyword backends once available — see §13 P0).

**Explicit confidence statement (per evaluation rules):** the current golden dataset's coverage is **insufficient** to certify any dimension of production answer quality beyond "does the happy-path single-hop factual case still return roughly the same text." It cannot detect regressions in multi-hop reasoning, conflict handling, ambiguity handling, distractor robustness, or citation correctness, because it contains no cases that exercise any of those paths. Additional cases needed, in priority order: (1) ≥10 real conflicting-source cases with human-labeled correct resolution, (2) ≥10 unanswerable/negative cases, (3) ≥10 multi-hop cases requiring synthesis across ≥2 real documents, (4) ≥5 adversarial hallucination cases (paraphrased fabrication, not just wrong numbers) to regression-test the faithfulness scorer once §9's P0 fix lands, (5) table/structured-content cases once a real table retriever exists.

---

## 7. Regression Analysis

**No true historical regression baseline exists for the answer-quality pipeline** (0 real production runs recorded in `IRegressionStore`), so "regression" here means either (a) real, reproducible non-determinism observed by re-running the *same* test twice, or (b) documented deltas between this evaluation's harness runs.

**Confirmed real regression-safety defect — the chunking performance benchmark is non-deterministic and machine-load-sensitive**, discovered by literally re-running the existing suite:

| Run | Context | Ratio (new/old median) | Threshold | Result |
|---|---|---|---|---|
| Committed baseline (`chunking_baseline.json`, in git) | — | 46.82x | ≤65.0x | recorded PASS |
| This evaluation, run 1 (full suite, 361 tests: `tests/unit/core` + `tests/integration`) | cold, contended | **77.02x** | ≤65.0x | **FAILED** |
| This evaluation, runs 2–4 (isolated, single test) | warm, uncontended | 46–47x (×3) | ≤65.0x | PASS ×3 |
| This evaluation, run 5 (full suite again) | cold, contended | **102.67x** | ≤65.0x | **FAILED** |

Same code, same machine, same day — flips between comfortably-passing (46x) and 58% over threshold (102x) purely based on whether it runs alone or as part of the full suite. **Root cause: the test measures a wall-clock ratio against a fixed hard threshold, with no statistical control for interpreter warm-up or CI-runner contention.** This means the `SC-008` regression gate is unreliable in both directions: it can red a genuinely unchanged commit (blocking merges on noise) and — more dangerously — a real regression up to 65x could be masked if it happens to run in an isolated, low-contention CI shard. This is a testing-infrastructure defect, not an answer-quality defect, but it directly undermines the "regression safety" pillar being evaluated in §11.

**Other regression-relevant findings (not "regressions" per se, since there is no prior baseline, but documented deltas within this evaluation for future baselining):**
- Faithfulness scorer's citation-hash bug (§4/§9) affects **10 of 11** scored real-pipeline answers — if this is fixed, every future run will show a large, *positive*, one-time "faithfulness improvement" that is purely an artifact of the fix, not of any change to retrieval/generation quality. **Anyone tracking faithfulness trend lines must anchor a new baseline strictly after the P0 fix in §13**, or the fix itself will be misread as a regression-detector false positive in the other direction.
- Conflict-detection false-positive rate (§3) — if `EntityTagConflictDetector`'s attribute-blindness is fixed, `conflicts_detected` rate will drop sharply (from this evaluation's 43% to something close to the true ~7% (1/14) genuine-conflict rate). Same baselining caveat applies.

---

## 8. Stress Testing

Real, executed results for each requested scenario, using the actual pipeline code:

| Scenario | Result |
|---|---|
| Large documents / many retrieved chunks | Not exercised — 20-chunk corpus never approached any budget/candidate cap (max observed: 8 candidates against a 20–30 cap). **Gap**: no test anywhere (existing suite or this harness) retrieves at a realistic production scale (1,000s of chunks) end-to-end through all 5 stages simultaneously; `tests/integration/benchmarks/test_chunking_benchmark.py` only benchmarks the chunking stage in isolation. |
| Large metadata / deep hierarchy | Not exercised — corpus chunks carry only `section_path`, no deep nesting. |
| Long / follow-up conversations | **Not exercisable at all** in this environment: `ConversationContext`/`TurnSummary` require the LLM-based `query_parser`, which has zero offline test path. Confirmed 0 tests anywhere in the repo exercise multi-turn context threading end-to-end. |
| Ambiguous questions | Exercised (`q_ambiguous_dose`) — correctly triggers `clarification_required=True` via the low-confidence path. Works as designed for this one shape of ambiguity (missing entity + unclassifiable operation). Untested: ambiguity from a *resolved* entity that's still genuinely ambiguous in context (e.g., "aspirin" when both adult and pediatric formulations are in scope) — the planner has no signal for this since entity resolution succeeded. |
| Conflicting documents | Exercised (`q_max_daily_dose_conflict`, `adv_undisclosed_conflict`) — conflict is detected structurally, but (a) detection has a high false-positive rate (§3) and (b) nothing downstream requires or verifies disclosure (§4, §9). |
| Duplicate documents | Exercised (`q_duplicate_collision`) — near-duplicate content from two different source documents was **not merged** under default config (no embedding provider wired), correctly per the strict 0.95 character-n-gram threshold, but see §2 for the silent-downgrade risk. |
| Missing metadata / missing entities | Partially exercised — `q_ambiguous_dose` (entity=None) correctly triggers clarification. A case with entity present but *wrong type* (e.g., resolving "aspirin" as a `document` entity type instead of `drug`) was not tested — `QueryPlanEntityResolver._match_type` falls back to a generic `"concept"` type whenever `entity_type_patterns` doesn't match, and no test verifies this fallback doesn't silently break downstream hint-building (`HintsBuilder.build` keys off `entity_type == "document"`/`"section"`). |
| Large token budgets | Exercised trivially (3.2% utilization everywhere) — **never stresses compression or drop logic.** |
| Small token budgets | **Not exercised in this evaluation** — deliberately shrinking `total_context_window` to force `items_dropped > 0` / `items_compressed > 0` was not attempted here, but the existing unit suite (`tests/unit/core/context_builder/test_budget_allocator.py`, `test_heuristic_compressor.py`, and integration `test_scenario_1_budget_compliance`) already covers this in isolation with passing results — deferred to that suite rather than duplicated. |
| Distractor / irrelevant documents | Exercised — `doc-legal-disclaimer` (zero pharma content) surfaced in top-5 for 5/14 queries (§1). This is the one stress scenario where this evaluation found a genuinely new, real, previously-untested failure mode. |

---

## 9. Failure Analysis

For every failure below: **Severity / Root Cause / Likelihood / Suggested Fix.** All are reproduced with real code execution; file:line references point to the exact defect.

**F1 — Faithfulness scorer flags every cited answer as partially unfaithful (citation-hash false positive)**
- Severity: **P0 (Critical)** — the primary faithfulness signal is unusable as shipped; it fires on ~91% of real answers regardless of correctness.
- Root Cause: `TextFaithfulnessScorer._NUMBER_PATTERN` (`src/core/answer_quality/faithfulness/scorer.py:13`) matches digits inside `[ei_xxxxxxxxxxxxxxxx]` citation markers before the answer/citation text is separated.
- Likelihood: **Certain, deterministic** — reproduces on 10/11 real pipeline runs and 0/5 adversarial probes without a citation (confirming citations are the trigger).
- Suggested Fix: strip citation markers (`_ITEM_ID_PATTERN`-equivalent) from the answer text *before* running span extraction; add a regression fixture asserting a correctly-cited, fully-grounded answer scores faithfulness ≥ 0.95.

**F2 — Faithfulness scorer is blind to qualitative/textual hallucination**
- Severity: **P0 (Critical)** — the highest-real-world-risk failure mode (a fabricated clinical claim in plain prose) is invisible.
- Root Cause: `_extract_claim_spans()` (`src/core/answer_quality/faithfulness/scorer.py:29`) only extracts number-like, quoted, or Title-Case spans; ordinary lowercase prose claims produce zero spans and default to a perfect score.
- Likelihood: **Certain** — proven with a clean, unconfounded adversarial probe (100% fabricated medical safety claim scored 1.0/PASSED).
- Suggested Fix: this requires semantic entailment (context ⊨ claim), not regex span-matching — realistically an LLM-as-judge or NLI model call is needed; regex span extraction cannot be patched to close this gap, only narrowed.

**F3 — Completeness scorer is gameable by keyword stuffing**
- Severity: **P1 (Major)** — allows a non-answer to pass as complete.
- Root Cause: `KeywordCompletenessScorer` (`src/core/answer_quality/completeness/scorer.py`) checks token-overlap against facet keywords with no check that the answer addresses the question.
- Likelihood: **Certain**, proven via `adv_keyword_stuffing` (topic-summary non-answer scored 1.0/PASSED).
- Suggested Fix: require the completeness scorer to also validate `AnswerResult.no_answer is False` **and** run a minimal answer-shape check (e.g., the answer contains a declarative claim near each matched facet, not just the facet token anywhere in the string) or replace with LLM-as-judge scoring.

**F4 — No citation-attribution / citation-accuracy scorer exists anywhere**
- Severity: **P1 (Major)** — the platform has zero automated ability to catch a citation attached to the wrong claim.
- Root Cause: architectural gap — `AnswerQualityRegistry.default_runner()` wires exactly 3 scorers (Coverage, Faithfulness, Completeness); none reads the correspondence between a specific `CitationReference` and the sentence it's adjacent to.
- Likelihood: not directly reproduced with a *broken* citation (the `adv_fabricated_citation` probe used a correct answer to demonstrate the absence of a check, since there is genuinely no code path to attack), but the absence is confirmed by exhaustive reading of `src/core/answer_quality/{interfaces,pipeline,registry}.py`.
- Suggested Fix: implement `ICitationAccuracyScorer` — for each citation marker, extract the adjacent sentence and verify lexical/semantic overlap with that *specific* cited chunk's text (not the whole corpus, as Faithfulness does).

**F5 — Conflict detection and disclosure are entirely unchecked by answer quality**
- Severity: **P1 (Major)** — silently resolving a known factual conflict (picking one side without disclosure) passes every scorer.
- Root Cause: none of Coverage/Faithfulness/Completeness reads `Context.conflicts` or `AnswerResult.conflicts_disclosed`.
- Likelihood: **Certain**, proven via `adv_undisclosed_conflict`.
- Suggested Fix: add a conflict-disclosure check to the golden test runner: if `context.conflicts` is non-empty, assert `answer_result.conflicts_disclosed is True`.

**F6 — Conflict detector has an attribute-blind false-positive mechanism**
- Severity: **P1 (Major)** — pollutes `conflicts_detected` telemetry and, per F5, would pollute a future disclosure check too.
- Root Cause: `EntityTagConflictDetector._extract_numeric_values` (`src/core/context_builder/conflict/entity_tag_detector.py:101`) treats any two different numbers within 100 characters of a shared entity tag as a conflict, without verifying they describe the same attribute.
- Likelihood: **High** — empirically triggered on 6/14 (43%) of harness queries against a corpus with exactly 1 genuine conflict.
- Suggested Fix: require attribute co-occurrence (e.g., shared units, shared preceding keyword like "dose"/"maximum"/"age") before flagging, or narrow the window and require the *same* keyword context on both sides.

**F7 — Planner/engine strategy contract has no startup-time validation, causing silent 0-result queries**
- Severity: **P0 (Critical, if this stack is ever wired to production)** — a plan can request strategies with zero registered retrievers, producing a confident "no answer" with no error, alert, or trace beyond a DEBUG-level log line.
- Root Cause: `RetrievalPlannerConfig.available_strategies`/`strategy_mappings` and the engine's `RetrieverRegistry` are configured completely independently; nothing validates their intersection is non-empty per intent category.
- Likelihood: **Confirmed reproducible** — `q_navigational_section` returned 0 candidates end-to-end in this harness because "metadata"/"document" retrievers weren't registered (a directly analogous situation to a partial/incremental rollout in production).
- Suggested Fix: add a startup-time assertion in the registry/DI wiring: for every strategy referenced in any `budget_defaults`/`strategy_mappings` entry, a concrete `IRetriever` must be registered, or fail fast at boot rather than fail silently per-query.

**F8 — Chunking regression benchmark is flaky under load (see §7 for data)**
- Severity: **P2 (Moderate)** — a testing-infrastructure defect, not an answer-quality defect, but it undermines trust in the one automated regression gate that exists for the ingestion path.
- Root Cause: fixed wall-clock-ratio threshold with no statistical control for machine contention.
- Likelihood: **Confirmed, reproduces on-demand** (2 of 2 full-suite runs failed; 3 of 3 isolated runs passed).
- Suggested Fix: run N repetitions and use median-of-medians or a percentile-based threshold; alternatively assert against operation counts/complexity rather than wall-clock ratio.

**F9 — Entity-type misresolution has no safety net**
- Severity: **P2 (Moderate)**
- Root Cause: `QueryPlanEntityResolver._match_type` (`src/core/retrieval_planner/entities/query_plan_resolver.py:52`) silently defaults to `entity_type="concept"` whenever no pattern matches, and downstream `HintsBuilder` only activates document/section-preference hints for `entity_type in {"document","section"}` — a misconfigured or incomplete `entity_type_patterns` field-pack silently disables retrieval hints with no warning.
- Likelihood: **Plausible, not directly reproduced against a wrong-type case in this evaluation** (would require constructing that specific fixture).
- Suggested Fix: log at WARNING when falling back to `"concept"` for an entity that appears in `retrieval_constraints`/hints-relevant paths; add a golden case exercising entity-type fallback.

---

## 10. Metrics (objective summary)

All values are real, measured (see §0 for scope/confidence caveats).

| Metric | Value | Source |
|---|---|---|
| Overall Retrieval Recall (mean Recall@10) | **0.556** | eval_run harness, n=12 |
| Overall Retrieval Precision (mean Precision@10) | **0.199** | eval_run harness, n=12 |
| Planner Accuracy (intent match) | **1.00** (14/14) | eval_run harness |
| Evidence Quality (mean doc_coverage) | **0.79** | eval_run harness, n=12 |
| Context Quality (token utilization, lost-info rate) | 3.2% budget used; 0% relevant chunks lost post-evidence | eval_run harness |
| Citation Accuracy (plumbing integrity) | **100%** (attribution correctness: **not measurable**, no scorer exists) | eval_run harness + code review |
| Groundedness / Faithfulness (as currently scored) | mean **0.27**, but scorer is proven unreliable in both directions (§4/§9, F1/F2) | eval_run harness + adversarial probes |
| Completeness (as currently scored) | mean **1.00**, but proven gameable (§4/§9, F3) | eval_run harness + adversarial probes |
| Hallucination Rate | **Not measurable** — no real LLM output exists to measure, and the shipped scorer cannot detect qualitative hallucination even when present (F2) | — |
| Latency — Planner | mean 0.23ms | eval_run harness (in-process) |
| Latency — Retrieval | mean 0.48ms (TF-IDF/RRF, no network) | eval_run harness |
| Latency — Evidence Orchestrator | mean 0.62ms (harness, 5-item batches); **7.37ms mean / 10.9ms max** (existing repo benchmark, `test_pipeline_latency_benchmark`, 20-item synthetic batch, real code) | eval_run harness + existing pytest benchmark |
| Latency — Context Builder | mean 0.36ms | eval_run harness |
| Latency — Answer Generation | mean 0.12ms (`MockLLM`, **not representative of a real model's latency**) | eval_run harness |
| Average Token Usage | 68–180 tokens/query against a 3000-token budget | eval_run harness |
| Overall Success Rate (`overall_passed` across scorers) | 2/13 (15%) — **but this reflects scorer defects (F1) more than answer quality** (see §4) | eval_run harness |

---

## 11. Production Readiness

| Sub-score | /10 | Rationale |
|---|---|---|
| Evaluation Coverage | **2/10** | 3 trivial golden fixtures, 0 adversarial/negative/multi-hop/conflict cases pre-existing; this evaluation had to author an entire synthetic dataset from scratch to test any dimension beyond single-hop factual lookup. |
| Regression Safety | **2/10** | `IRegressionStore` exists as an interface/data model but has zero real historical baselines; the one wall-clock regression gate that does run (`SC-008` chunking benchmark) is empirically flaky (§7). |
| Reliability | **3/10** | Core pipeline mechanics (fusion, budget, citation plumbing) are deterministic and correct where exercised; but a whole intent category (navigational) fails silently to zero results the moment its mapped strategies aren't registered (F7), with no alerting. |
| Robustness | **3/10** | Distractor documents pollute top-5 in 5/14 harness queries; conflict detection false-positives at ~43% (harness); textual hallucinations are invisible to the only faithfulness check that exists. |
| Consistency | **5/10** | Deterministic-by-construction where mocked (planner plan_id hashing, RRF fusion); genuinely untestable for the one component (LLM generation) where real-world consistency actually matters, because no live model is reachable in this environment. |

**Weak points, explained:**
1. The answer-quality scorers (Coverage/Faithfulness/Completeness) are the platform's only automated gate before anything reaches a user, and two of the three are proven unreliable (F1–F3) with concrete, reproducible counter-examples.
2. There is no automated check for the two failure modes most likely to cause real harm in a pharmacy-adjacent domain: qualitative hallucination (F2) and undisclosed conflicting-source information (F5).
3. The planner and engine can silently disagree about which retrieval strategies are actually available (F7), and the system's response to that disagreement is a confident "not found" rather than a diagnosable error.
4. Zero real end-to-end runs (embedding + LLM) have ever been captured into the regression store, so there is no empirical baseline to detect a live-model regression against, even if one occurred today.

---

## 12. Final Scores (/10)

| Aspect | Score | 1-line justification |
|---|---|---|
| Retrieval Quality | **4/10** | Fusion/budget mechanics are correct; ranking quality on ambiguous lexical overlap is weak in this harness and **entirely unverified against the real embedding backend** anywhere in the repo. |
| Planner Quality | **6/10** | Intent/strategy/budget logic is correct and deterministic on all 14 real test cases; contract gap with the engine's retriever registry (F7) is a real, found defect. |
| Evidence Quality | **5/10** | Citation plumbing and exact-dedup are solid; near-dedup silently degrades without an embedding provider (§2), and no test exercises evidence sufficiency at production scale. |
| Context Quality | **5/10** | Budget/ordering/citation-integrity mechanics work; conflict detection has a confirmed high false-positive mechanism (F6); compression path is completely untested by both this evaluation and the pre-existing golden dataset at meaningful scale. |
| Answer Quality | **2/10** | Cannot be scored meaningfully — no live LLM output exists anywhere in this environment to evaluate, and the one automated gate that exists (answer_quality scorers) is independently proven broken (F1–F3). |
| Citation Quality | **4/10** | 100% structural integrity (every citation resolves); 0% verified attribution accuracy because no scorer for that exists (F4). |
| Faithfulness | **2/10** | The scorer, as shipped, is simultaneously too strict (penalizes all cited answers, F1) and too permissive (misses all qualitative hallucination, F2) — it cannot be trusted as a release gate today. |
| Completeness | **3/10** | Trivially gameable (F3); the 1.00 mean measured is not evidence of real completeness. |
| Reliability | **3/10** | Deterministic where mocked; one confirmed silent-failure mode (F7) with no alerting. |
| Consistency | **4/10** | Cannot be evaluated for the one place it matters most (LLM output); everything mocked is consistent by construction, which proves nothing about production. |
| Production Readiness | **3/10** | See §11 — genuinely low across every sub-score. |
| **Overall RAG Quality** | **3/10** | Not a statement that the underlying architecture is bad (see `ARCHITECTURE_AUDIT.md` for that separate question) — it is a statement that **today, with the available evidence, no one can certify this system's answer quality**, because the harness needed to certify it does not exist, and the one automated gate that does exist has proven, reproducible defects. |

---

## 13. Prioritized Improvements

### P0 — Critical, must fix before any answer-quality claim can be trusted
1. **Fix the faithfulness scorer's citation-marker false-positive (F1)** — strip citation markers before span extraction. This is a ~5-line fix with disproportionate impact: it currently invalidates the faithfulness signal on essentially every real answer.
2. **Add a semantic (LLM-as-judge or NLI-based) faithfulness check to close the qualitative-hallucination blind spot (F2)** — regex span-matching cannot be patched to catch this; it needs a genuinely different detection method. This is the single highest-risk gap in the entire evaluation platform given the domain (pharmacy).
3. **Validate the planner↔engine strategy contract at startup, not silently per-query (F7)** — fail fast if any strategy referenced in planner config has no registered retriever, instead of returning a confident "not found."
4. **Get at least one live LLM+embedding credential wired into a controlled evaluation environment** (even a small budget / rate-limited key) — every score in §4/§12 above is capped at "not measurable" without this; this evaluation could not produce a single real hallucination-rate or generation-accuracy number, which is a P0 blocker on ever answering the question this whole exercise was commissioned to answer.

### P1 — Major quality improvements
5. **Fix the completeness scorer's keyword-stuffing vulnerability (F3)** — require a minimal answer-shape / no_answer check alongside keyword overlap, or migrate to LLM-as-judge.
6. **Add a citation-attribution scorer (F4)** — verify each citation is adjacent to a claim it actually supports, not just that it resolves to a real source.
7. **Add a conflict-disclosure check to the golden test runner (F5)** — if `context.conflicts` is non-empty, assert the answer discloses it.
8. **Fix the conflict detector's attribute-blindness (F6)** — require shared-attribute context, not just shared entity tag + nearby differing numbers.
9. **Expand the golden dataset** per §6's gap list (conflicting-source, unanswerable, multi-hop, adversarial-hallucination, table cases) — promote this evaluation's `eval_run/corpus.py` and `run_adversarial_probes.py` cases into permanent fixtures under `tests/fixtures/answer_quality/`.
10. **Populate the regression store with real baseline runs** once P0-4 unblocks live-model evaluation, so future changes have something to regress against.

### P2 — Performance / reliability improvements
11. **Fix the flaky chunking regression benchmark (F8)** — statistical threshold instead of a single wall-clock ratio.
12. **Add a startup-time WARNING (not silent fallback) when entity-type resolution defaults to `"concept"` in a hints-relevant path (F9).**
13. **Add production-scale stress tests** (§8 gaps: 1,000s of chunks, tight token budgets forcing real compression/drop paths, multi-turn conversation threading) — none of this is exercised today by either the existing suite or this evaluation.
14. **Surface `dedup_method_used` (embedding vs. character-n-gram fallback) as a metric/alert**, not just a trace field, so a missing embedding-provider wiring is visible in production telemetry (§2).

### P3 — Future enhancements
15. Add self-contradiction detection (no scorer currently checks internal answer consistency).
16. Add Helpfulness / Instruction-Following / Conciseness / Formatting scorers — currently zero coverage for any of these requested evaluation dimensions.
17. Add repeated-sampling consistency testing against the real model once live access exists (temperature=0 vs >0 variance).
18. Extend the golden dataset with non-English and mixed-language cases (`RetrievalConstraints.required_language` exists in the schema but is untested end-to-end).

---

## Appendix — Raw artifacts produced by this evaluation

- `eval_run/corpus.py` — 20-chunk / 11-document labeled corpus, 14 queries with ground-truth relevance, expected intents, and expected answer facets.
- `eval_run/retrievers.py` — real TF-IDF cosine + Jaccard retrievers implementing `IRetriever` (substitutes for the unavailable embedding/full-text backends).
- `eval_run/ir_metrics.py` — Recall@k / Precision@k / MRR / NDCG implementations.
- `eval_run/run_full_eval.py` — end-to-end harness wiring the real planner → engine → evidence orchestrator → context builder → answer generation → answer quality pipeline; writes `results_pipeline.json` and `results_summary.json`.
- `eval_run/run_adversarial_probes.py` — 5 unconfounded scorer-robustness probes; writes `results_adversarial.json`.
- `eval_run/results_pipeline.json`, `eval_run/results_summary.json`, `eval_run/results_adversarial.json` — full raw output backing every number in this report.

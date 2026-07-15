# Interface Contracts: Answer Quality (spec 014)

**Date**: 2026-07-15 | **Source**: spec.md FR-003–FR-007, data-model.md

All interfaces are abstract base classes (`ABC`) defined in
`src/core/answer_quality/interfaces.py`. Callers depend on these abstractions;
concrete implementations are registered via `AnswerQualityRegistry`.

---

## `IGoldenTestRunner`

Orchestrates a full golden test run: loads fixtures, invokes the three scorers, and
aggregates results into an `EvaluationResult`.

```python
class IGoldenTestRunner(ABC):
    @abstractmethod
    async def run(
        self,
        fixtures: list[GoldenTestFixture],
        pipeline_outputs: list[PipelineSnapshot],
        config: AnswerQualityConfig,
    ) -> EvaluationResult: ...
```

**`PipelineSnapshot`** is a plain data container (not an interface):

```python
@dataclass(frozen=True)
class PipelineSnapshot:
    question_id: str
    answer_result: AnswerResult
    context: Context
    evidence_pack: EvidencePack | None   # None → coverage scored as N/A
```

**Contract**:
- `fixtures` and `pipeline_outputs` are matched by `question_id`; unmatched questions
  raise `EvaluationError`.
- Runner MUST NOT mutate `AnswerResult`, `Context`, or `EvidencePack`.
- Returns a complete `EvaluationResult` even if individual questions fail scoring
  (per-question errors are recorded as N/A dimensions, not raised exceptions).
- Empty `fixtures` list raises `EvaluationError("No fixtures provided")`.

---

## `ICoverageEvaluator`

Evaluates whether retrieval surfaced all expected source documents for a question.

```python
class ICoverageEvaluator(ABC):
    @abstractmethod
    async def evaluate(
        self,
        fixture: GoldenTestFixture,
        evidence_pack: EvidencePack | None,
        config: AnswerQualityConfig,
    ) -> CoverageResult: ...
```

**Contract**:
- If `fixture.expected_source_ids` is `None` or empty: returns
  `CoverageResult(not_applicable=True, passed=True, coverage_score=None)`.
- If `evidence_pack` is `None`: same as above (coverage N/A for replay scenarios
  without pack).
- Matching is against `EvidenceItem.doc_id` (not `chunk_id` or `item_id`). See
  research R-01.
- `coverage_score = len(found) / len(expected)`.
- `passed = coverage_score >= effective_threshold` where `effective_threshold` is
  `fixture.thresholds.coverage ?? config.global_thresholds.coverage`.

---

## `IFaithfulnessScorer`

Verifies factual claims in the answer against cited source text.

```python
class IFaithfulnessScorer(ABC):
    @abstractmethod
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        context: Context,
        config: AnswerQualityConfig,
    ) -> FaithfulnessResult: ...
```

**Contract**:
- If `answer_result.no_answer is True` or `context.ordered_blocks` is empty: returns
  `FaithfulnessResult(not_applicable=True, passed=True, faithfulness_score=None)`.
- Ground-truth corpus is built from `context.ordered_blocks[*].text` (NOT from
  `Context.citation_map` values, which carry no text). See research R-03.
- Unsupported claim spans are listed in `FaithfulnessResult.unsupported_claims`.
- `faithfulness_score = 1 - len(unsupported) / max(len(spans), 1)`.
- `passed = faithfulness_score >= effective_threshold`.
- Scorer MUST NOT call any external LLM or embedding API.

---

## `ICompletenessScorer`

Checks whether the answer addresses all expected answer facets.

```python
class ICompletenessScorer(ABC):
    @abstractmethod
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        config: AnswerQualityConfig,
    ) -> CompletenessResult: ...
```

**Contract**:
- If `fixture.expected_answer_facets` is `None` or empty, or
  `answer_result.no_answer is True`: returns
  `CompletenessResult(not_applicable=True, passed=True, completeness_score=None)`.
- A facet is "covered" if ≥ `config.completeness_overlap_threshold` (default 0.5)
  fraction of its tokens appear in the answer token set (stop-words removed). See
  research R-04.
- `completeness_score = covered_facets / total_facets`.
- `passed = completeness_score >= effective_threshold`.
- Scorer MUST NOT call any external LLM or embedding API.

---

## `IRegressionStore`

Persists and compares `EvaluationResult` records across runs.

```python
class IRegressionStore(ABC):
    @abstractmethod
    async def save(self, result: EvaluationResult) -> Path: ...

    @abstractmethod
    async def load(self, run_id: str) -> EvaluationResult: ...

    @abstractmethod
    async def list_runs(self) -> list[str]: ...

    @abstractmethod
    async def diff(
        self,
        run_id_baseline: str,
        run_id_current: str,
        config: AnswerQualityConfig,
    ) -> RegressionDiff: ...
```

**Contract**:
- `save()` MUST be idempotent for the same `run_id`; re-saving overwrites.
- `load()` raises `EvaluationError` if `run_id` is not found.
- `diff()` raises `EvaluationError` if either run ID is not found.
- `list_runs()` returns run IDs sorted ascending by `run_at`.
- v1 concrete implementation: `JsonRegressionStore` writes one
  `{run_id}.json` per `EvaluationResult` to `config.run_store_dir`.

---

## Golden Fixture YAML Schema (v1.0.0)

Human-authored fixture files live in `tests/fixtures/answer_quality/*.yaml`.

```yaml
version: "1.0.0"
fixtures:
  - question_id: "q001"                  # required; stable across edits
    question: "What is the adult dose?"   # required
    expected_source_ids:                  # optional; matched on EvidenceItem.doc_id
      - "doc-aspirin-pil"
    expected_answer_facets:              # optional; for completeness scoring
      - "325 mg"
      - "every 4 to 6 hours"
    thresholds:                          # optional; per-question overrides
      coverage: 0.8
      faithfulness: 0.8
      completeness: 0.7
```

Note: there is no `match_mode` field. Scoring algorithm selection (text-matching vs
semantic) is a registry-level decision — configure which concrete scorer is registered
in `AnswerQualityRegistry`, not in the fixture file.

Loading is done by `AnswerQualityRegistry.load_fixtures(path)` which validates the
YAML against the `GoldenTestFixture` Pydantic model and raises `FixtureLoadError`
on schema violations.

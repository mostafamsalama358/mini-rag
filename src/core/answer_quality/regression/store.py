"""JSON file regression store."""

from __future__ import annotations

from pathlib import Path

from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.errors import RunNotFoundError
from core.answer_quality.interfaces import IRegressionStore
from core.answer_quality.models import EvaluationResult, QuestionDelta, RegressionDiff


class JsonRegressionStore(IRegressionStore):
    def __init__(self, run_store_dir: str | Path | None = None) -> None:
        self._default_run_store_dir = (
            str(run_store_dir) if run_store_dir is not None else None
        )

    def _store_dir(self, config: AnswerQualityConfig) -> Path:
        if self._default_run_store_dir is not None:
            return Path(self._default_run_store_dir)
        return Path(config.run_store_dir)

    def _run_path(self, run_id: str, config: AnswerQualityConfig) -> Path:
        return self._store_dir(config) / f"{run_id}.json"

    async def save(self, result: EvaluationResult) -> Path:
        config = AnswerQualityConfig(run_store_dir=self._default_run_store_dir or ".answer_quality/runs")
        path = self._run_path(result.run_id, config)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json(), encoding="utf-8")
        return path

    async def load(self, run_id: str) -> EvaluationResult:
        config = AnswerQualityConfig(run_store_dir=self._default_run_store_dir or ".answer_quality/runs")
        path = self._run_path(run_id, config)
        if not path.exists():
            raise RunNotFoundError(f"Run not found: {run_id}")
        return EvaluationResult.model_validate_json(path.read_text(encoding="utf-8"))

    async def list_runs(self) -> list[str]:
        config = AnswerQualityConfig(run_store_dir=self._default_run_store_dir or ".answer_quality/runs")
        base = self._store_dir(config)
        if not base.exists():
            return []
        runs: list[tuple[str, str]] = []
        for path in base.glob("*.json"):
            run_id = path.stem
            result = EvaluationResult.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            runs.append((result.run_at, run_id))
        runs.sort(key=lambda item: item[0])
        return [run_id for _, run_id in runs]

    async def diff(
        self,
        run_id_baseline: str,
        run_id_current: str,
        config: AnswerQualityConfig,
    ) -> RegressionDiff:
        baseline_path = self._run_path(run_id_baseline, config)
        current_path = self._run_path(run_id_current, config)
        if not baseline_path.exists():
            raise RunNotFoundError(f"Run not found: {run_id_baseline}")
        if not current_path.exists():
            raise RunNotFoundError(f"Run not found: {run_id_current}")

        baseline = EvaluationResult.model_validate_json(
            baseline_path.read_text(encoding="utf-8")
        )
        current = EvaluationResult.model_validate_json(
            current_path.read_text(encoding="utf-8")
        )
        baseline_by_id = {item.question_id: item for item in baseline.question_results}
        current_by_id = {item.question_id: item for item in current.question_results}

        regressions: list[QuestionDelta] = []
        improvements: list[QuestionDelta] = []
        stable: list[str] = []
        threshold = config.regression_threshold

        all_question_ids = sorted(set(baseline_by_id) | set(current_by_id))
        for question_id in all_question_ids:
            base_result = baseline_by_id.get(question_id)
            curr_result = current_by_id.get(question_id)
            if base_result is None or curr_result is None:
                continue

            dimension_pairs = [
                ("coverage", base_result.coverage.coverage_score, curr_result.coverage.coverage_score),
                (
                    "faithfulness",
                    base_result.faithfulness.faithfulness_score,
                    curr_result.faithfulness.faithfulness_score,
                ),
                (
                    "completeness",
                    base_result.completeness.completeness_score,
                    curr_result.completeness.completeness_score,
                ),
            ]
            question_changed = False
            for dimension, base_score, curr_score in dimension_pairs:
                if base_score is None or curr_score is None:
                    continue
                delta = curr_score - base_score
                if abs(delta) < threshold:
                    continue
                question_changed = True
                delta_obj = QuestionDelta(
                    question_id=question_id,
                    dimension=dimension,  # type: ignore[arg-type]
                    baseline_score=base_score,
                    current_score=curr_score,
                    delta=delta,
                )
                if delta < 0:
                    regressions.append(delta_obj)
                else:
                    improvements.append(delta_obj)
            if not question_changed:
                stable.append(question_id)

        return RegressionDiff(
            run_id_baseline=run_id_baseline,
            run_id_current=run_id_current,
            regressions=regressions,
            improvements=improvements,
            stable=stable,
            has_regressions=len(regressions) > 0,
        )

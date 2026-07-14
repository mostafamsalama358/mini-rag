"""Unit tests for Retrieval Planner models and static import constraints."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.retrieval_planner.models import (
    SCHEMA_VERSION,
    ExecutionHints,
    OutputShape,
    PlannerDiagnostics,
    QueryIntent,
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalPlan,
    RetrievalPlanMetadata,
    RetrievalPlannerConfig,
    StrategyType,
)


def _minimal_plan(**overrides) -> RetrievalPlan:
    base = dict(
        intent=QueryIntent(category="factual", confidence=0.9),
        entities=(),
        filters=(),
        retrieval_strategies=("semantic",),
        retrieval_limits=RetrievalLimits(
            max_evidence_units=5, max_candidates=20, scope="narrow"
        ),
        retrieval_constraints=RetrievalConstraints(citation_required=True),
        execution_hints=None,
        output_shape=OutputShape(shape_type="single_fact", max_items=None, structured=False),
        clarification_required=False,
        clarification_question=None,
        planner_confidence=0.9,
        diagnostics=None,
        metadata=RetrievalPlanMetadata(
            plan_id="rp_" + "a" * 16,
            planner_version="1.0.0",
            schema_version=SCHEMA_VERSION,
            config_hash="deadbeef",
            created_at="2026-07-14T00:00:00Z",
        ),
    )
    base.update(overrides)
    return RetrievalPlan(**base)


def test_retrieval_plan_is_frozen():
    plan = _minimal_plan()
    with pytest.raises(ValidationError):
        plan.planner_confidence = 0.1  # type: ignore[misc]


def test_strategy_type_accepts_any_nonempty_string():
    # StrategyType is an open Annotated[str, Field(min_length=1)] type.
    from typing import get_args

    from pydantic import TypeAdapter

    adapter = TypeAdapter(StrategyType)
    assert adapter.validate_python("citations_graph") == "citations_graph"
    with pytest.raises(ValidationError):
        adapter.validate_python("")
    cfg = RetrievalPlannerConfig(available_strategies=["citations_graph", "semantic"])
    assert "citations_graph" in cfg.available_strategies


def test_plan_id_format():
    plan = _minimal_plan()
    assert plan.metadata.plan_id.startswith("rp_")
    assert len(plan.metadata.plan_id) == 19


def test_schema_version_is_100():
    plan = _minimal_plan()
    assert plan.metadata.schema_version == "1.0.0"
    assert re.fullmatch(r"\d+\.\d+\.\d+", plan.metadata.schema_version)


def test_clarification_validator_rejects_strategies_when_required():
    with pytest.raises(ValidationError):
        _minimal_plan(
            clarification_required=True,
            clarification_question="What do you mean?",
            retrieval_strategies=("semantic",),
        )


def test_clarification_validator_requires_question():
    with pytest.raises(ValidationError):
        _minimal_plan(
            clarification_required=True,
            clarification_question=None,
            retrieval_strategies=(),
        )


def test_clarification_ok_with_empty_strategies():
    plan = _minimal_plan(
        clarification_required=True,
        clarification_question="Can you clarify?",
        retrieval_strategies=(),
        planner_confidence=0.3,
    )
    assert plan.clarification_required is True
    assert plan.retrieval_strategies == ()


_FORBIDDEN_MODULES = {
    "core.retrieval",
    "stores.vectordb",
    "stores.llm",
    "psycopg2",
    "psycopg",
    "asyncpg",
    "sqlalchemy",
    "bm25",
    "rank_bm25",
}


def _collect_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0] if "." not in alias.name else alias.name)
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            parts = node.module.split(".")
            if len(parts) >= 2:
                found.add(".".join(parts[:2]))
    return found


def test_no_retrieval_imports():
    root = Path(__file__).resolve().parents[4] / "src" / "core" / "retrieval_planner"
    assert root.is_dir(), f"missing package root: {root}"
    offenders: list[str] = []
    for py in root.rglob("*.py"):
        imports = _collect_imports(py)
        for forbidden in _FORBIDDEN_MODULES:
            if forbidden in imports or any(
                imp == forbidden or imp.startswith(forbidden + ".") for imp in imports
            ):
                offenders.append(f"{py.relative_to(root.parent.parent.parent)}: {forbidden}")
    assert not offenders, f"forbidden imports found: {offenders}"


def test_sc010_open_strategy_in_config():
    cfg = RetrievalPlannerConfig(
        available_strategies=["citations_graph", "semantic"],
        strategy_mappings={"factual": ["citations_graph", "semantic"]},
    )
    assert "citations_graph" in cfg.available_strategies
    assert cfg.strategy_mappings["factual"][0] == "citations_graph"


def test_sc011_schema_version_semver():
    plan = _minimal_plan()
    assert plan.metadata.schema_version == SCHEMA_VERSION
    assert re.fullmatch(r"\d+\.\d+\.\d+", plan.metadata.schema_version)


def test_execution_hints_mutable_at_construction():
    hints = ExecutionHints()
    hints.allow_table_search = True
    assert hints.allow_table_search is True


def test_diagnostics_mutable():
    d = PlannerDiagnostics()
    d.clarification_trigger = "empty_query"
    assert d.clarification_trigger == "empty_query"

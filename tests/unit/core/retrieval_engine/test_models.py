"""Unit tests for Retrieval Engine models and static import constraints."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.retrieval_engine.models import (
    SCHEMA_VERSION,
    ExpansionResult,
    RawCandidate,
    RetrievalContext,
    RetrievalExecutionMetadata,
    RetrievalQuery,
    RetrievalResult,
    RetrievedCandidate,
    RetrievalTrace,
    SourceRef,
    compute_result_id,
)
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_planner.models import RetrievalConstraints


def test_retrieval_result_is_frozen():
    result_id = compute_result_id("rp_" + "a" * 16, ["semantic"], "rrf", "passthrough")
    result = RetrievalResult(
        result_id=result_id,
        plan_id="rp_" + "a" * 16,
        candidates=(),
        trace=RetrievalTrace(plan_id="rp_" + "a" * 16),
        metadata=RetrievalExecutionMetadata(
            result_id=result_id,
            plan_id="rp_" + "a" * 16,
        ),
    )
    with pytest.raises(ValidationError):
        result.partial = True  # type: ignore[misc]


def test_result_id_format_and_determinism():
    a = compute_result_id("rp_abcd", ["semantic", "keyword"], "rrf", "passthrough")
    b = compute_result_id("rp_abcd", ["keyword", "semantic"], "rrf", "passthrough")
    assert a == b
    assert a.startswith("rr_")
    assert len(a) == 19


def test_schema_version():
    assert SCHEMA_VERSION == "1.0.0"


def test_retrieved_candidate_rank_one_based():
    c = RetrievedCandidate(
        chunk_id="c1",
        document_id="d1",
        score=0.5,
        score_source="raw",
        rank=1,
    )
    assert c.rank == 1
    with pytest.raises(ValidationError):
        RetrievedCandidate(
            chunk_id="c1",
            document_id="d1",
            score=0.5,
            score_source="raw",
            rank=0,
        )


def test_retrieval_query_has_exactly_three_fields():
    fields = set(RetrievalQuery.model_fields)
    assert fields == {"query_text", "strategy", "expander_variant_id"}


def test_retrieval_context_carries_policy():
    ctx = RetrievalContext(
        plan_id="rp_x",
        filters=(),
        constraints=RetrievalConstraints(),
        hints=None,
        policy=ExecutionPolicy(),
    )
    assert isinstance(ctx.policy, ExecutionPolicy)


def test_expansion_result_requires_variants():
    with pytest.raises(ValidationError):
        ExpansionResult(variants=(), expansion_type="x")


_FORBIDDEN = {
    "stores.vectordb",
    "stores.llm",
    "utils.rerank",
    "repositories",
    "psycopg2",
    "asyncpg",
}


def _collect_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            parts = node.module.split(".")
            if len(parts) >= 2:
                found.add(".".join(parts[:2]))
            found.add(parts[0])
    return found


def test_no_infra_imports_in_engine_core():
    root = Path(__file__).resolve().parents[4] / "src" / "core" / "retrieval_engine"
    assert root.is_dir()
    skip = {"graph.py", "sql.py"}
    offenders: list[str] = []
    for py in root.rglob("*.py"):
        if py.name in skip:
            continue
        imports = _collect_imports(py)
        for forbidden in _FORBIDDEN:
            if any(
                imp == forbidden or imp.startswith(forbidden + ".") for imp in imports
            ):
                offenders.append(f"{py}: {forbidden}")
    assert not offenders, offenders

"""T014 — frozen /answer field names from 015 remain the contract."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT, read

API_STABILITY = (
    REPO_ROOT
    / "specs"
    / "015-unified-pipeline-migration"
    / "contracts"
    / "api-stability.md"
)
COMPAT_020 = (
    REPO_ROOT
    / "specs"
    / "020-pharmacy-recommendation"
    / "contracts"
    / "compatibility.md"
)


def test_020_compatibility_cites_frozen_fields() -> None:
    text = read(COMPAT_020)
    for field in ("text", "limit", "session_id", "metadata_filter", "signal", "answer", "needs_clarification"):
        assert field in text


def test_015_api_stability_still_lists_answer_fields() -> None:
    text = read(API_STABILITY)
    assert "POST /api/v1/nlp/{project_id}/answer" in text
    assert "`answer`" in text or '"answer"' in text
    assert "needs_clarification" in text

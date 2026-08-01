"""021 — frozen /answer response fields remain; skill_id is request-only."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT, read

API_STABILITY = (
    REPO_ROOT
    / "specs"
    / "015-unified-pipeline-migration"
    / "contracts"
    / "api-stability.md"
)
COMPAT_021 = (
    REPO_ROOT
    / "specs"
    / "021-domain-skill-framework"
    / "contracts"
    / "compatibility.md"
)
SCHEMES = REPO_ROOT / "src" / "routes" / "schemes" / "nlp.py"


def test_021_compatibility_cites_frozen_response_fields() -> None:
    text = read(COMPAT_021)
    for field in ("signal", "answer", "needs_clarification"):
        assert field in text


def test_015_api_stability_still_lists_answer_fields() -> None:
    text = read(API_STABILITY)
    assert "needs_clarification" in text
    assert "`answer`" in text or '"answer"' in text


def test_answer_request_has_additive_skill_id() -> None:
    text = SCHEMES.read_text(encoding="utf-8")
    assert "skill_id" in text

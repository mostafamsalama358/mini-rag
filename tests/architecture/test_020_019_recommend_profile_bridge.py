"""T054 — 019 profile bridge for pharmacy recommend."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT, read

PROFILE_INDEX = (
    REPO_ROOT
    / "specs"
    / "019-rag-evaluation-framework"
    / "governance"
    / "evaluation-profile-index.md"
)


def test_019_has_pharmacy_recommend_profile_bridge() -> None:
    text = read(PROFILE_INDEX)
    assert "pharmacy" in text.casefold() or "recommend" in text.casefold()
    assert "020" in text or "recommend" in text.casefold()

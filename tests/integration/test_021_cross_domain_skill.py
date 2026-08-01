"""US5 — cross-domain skill_id rejected."""

from __future__ import annotations

import pytest

from services.FieldRegistry import get_field_registry
from services.rag.skills import SkillResolutionError, resolve_skill


def test_pharmacy_skill_on_legal_rejected() -> None:
    legal = get_field_registry().build_profile("legal")
    with pytest.raises(SkillResolutionError):
        resolve_skill(legal, "interactions")

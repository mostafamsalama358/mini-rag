"""Backward-compat alias — prefer SkillExecutionContext."""

from __future__ import annotations

from services.rag.skills.context import SkillExecutionContext

# Historical name used in early 021 tests/docs.
SelectedSkillBinding = SkillExecutionContext

__all__ = ["SelectedSkillBinding", "SkillExecutionContext"]

"""Load per-Skill prompt templates from Domain Pack prompts/skills/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from string import Template

_FIELDS_DIR = Path(__file__).resolve().parents[3] / "fields"


@lru_cache(maxsize=64)
def _read_skill_prompt(domain_key: str, prompt_ref: str) -> str | None:
    base = _FIELDS_DIR / domain_key / "prompts" / "skills"
    if not base.is_dir():
        return None
    for name in (f"{prompt_ref}.jinja", f"{prompt_ref}.txt", f"{prompt_ref}.md"):
        path = base / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def load_skill_prompt(domain_key: str, prompt_ref: str, *, variables: dict | None = None) -> str | None:
    """Return Skill-owned prompt text, or None if missing (caller falls back)."""
    text = _read_skill_prompt(domain_key, prompt_ref)
    if text is None:
        return None
    try:
        return Template(text).safe_substitute(variables or {})
    except Exception:
        return text

"""Robust extraction of a single JSON object from LLM text."""
from __future__ import annotations

import json
import re

_NON_GREEDY_JSON_RE = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}")


def extract_json_object(text: str) -> str | None:
    """Return the first complete top-level JSON object found in *text*.

    Preferred order:
    1. Whole stripped string when it is valid JSON (native JSON mode).
    2. Balanced-brace scan from the first ``{``.
    3. Non-greedy regex fallback.
    """
    stripped = (text or "").strip()
    if not stripped:
        return None

    if stripped.startswith("{"):
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            pass

    balanced = _balanced_brace_extract(stripped)
    if balanced is not None:
        return balanced

    match = _NON_GREEDY_JSON_RE.search(stripped)
    if match:
        return match.group(0)

    return None


def _balanced_brace_extract(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None

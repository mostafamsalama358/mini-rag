"""JSON-first LLM output parser with plain-text fallback."""

from __future__ import annotations

import json

from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.errors import AnswerGenerationError
from core.answer_generation.interfaces import IOutputParser


class JsonOutputParser(IOutputParser):
    def parse(
        self,
        raw: str,
        config: AnswerGenerationConfig,
    ) -> tuple[str, str | None]:
        _ = config
        if raw is None or not isinstance(raw, str):
            raise AnswerGenerationError(
                f"unparseable LLM response: expected str, got {type(raw).__name__}"
            )

        stripped = raw.strip()
        if not stripped:
            return "", None

        answer_text: str | None = None
        confidence_note: str | None = None

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, dict):
            answer_value = parsed.get("answer")
            if answer_value is None:
                answer_text = stripped
                confidence_note = None
            elif isinstance(answer_value, str):
                answer_text = answer_value
                note_value = parsed.get("confidence_note")
                confidence_note = note_value if isinstance(note_value, str) else None
            else:
                raise AnswerGenerationError(
                    "unparseable LLM response: JSON 'answer' field is not a string "
                    f"(len={len(raw)}, preview={raw[:100]!r})"
                )
        else:
            answer_text = stripped
            confidence_note = None

        if not answer_text or not answer_text.strip():
            return "", None

        return answer_text.strip(), confidence_note

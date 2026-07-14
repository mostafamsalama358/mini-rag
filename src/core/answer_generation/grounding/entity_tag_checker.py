"""Lightweight entity-tag grounding checker (flag-only, fail-open)."""

from __future__ import annotations

import logging
import re

from core.answer_generation.interfaces import IGroundingChecker
from core.answer_generation.models import GroundingFlag
from core.context_builder.models import Context

logger = logging.getLogger(__name__)

_ENTITY_PATTERN = re.compile(
    r"\b((?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,}))+)\b"
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_LEADING_STOPWORDS = frozenset(
    {
        "A",
        "An",
        "If",
        "Patient",
        "Sources",
        "The",
        "This",
        "That",
        "Use",
        "When",
    }
)


def _build_context_vocabulary(context: Context) -> set[str]:
    words: set[str] = set()
    for block in context.ordered_blocks:
        for token in re.findall(r"[A-Za-z0-9]+", block.text.lower()):
            words.add(token)
    return words


def _normalize_entity(entity: str) -> str:
    parts = entity.split()
    while parts and parts[0] in _LEADING_STOPWORDS:
        parts = parts[1:]
    return " ".join(parts)


def _entity_in_vocabulary(entity: str, vocabulary: set[str]) -> bool:
    entity_tokens = re.findall(r"[A-Za-z0-9]+", entity.lower())
    if not entity_tokens:
        return True
    return all(token in vocabulary for token in entity_tokens)


def _claim_for_entity(answer_text: str, entity: str) -> str:
    for sentence in _SENTENCE_SPLIT.split(answer_text.strip()):
        if entity in sentence:
            return sentence.strip()
    return answer_text.strip()


class EntityTagGroundingChecker(IGroundingChecker):
    def check(
        self,
        answer_text: str,
        context: Context,
    ) -> list[GroundingFlag]:
        try:
            if not answer_text.strip():
                return []

            vocabulary = _build_context_vocabulary(context)
            flags: list[GroundingFlag] = []
            seen_entities: set[str] = set()

            for match in _ENTITY_PATTERN.finditer(answer_text):
                entity = _normalize_entity(match.group(1))
                if not entity or entity in seen_entities:
                    continue
                seen_entities.add(entity)

                if _entity_in_vocabulary(entity, vocabulary):
                    continue

                flags.append(
                    GroundingFlag(
                        entity=entity,
                        claim=_claim_for_entity(answer_text, entity),
                        reason="entity_not_in_context",
                    )
                )

            return flags
        except Exception as exc:
            logger.warning(
                "grounding_checker_fail_open context_id=%s error=%s",
                context.context_id,
                exc,
            )
            return []

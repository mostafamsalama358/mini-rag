"""Entity-tag based conflict detection."""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.interfaces import IConflictDetector
from core.context_builder.models import ConflictGroup
from core.evidence_orchestrator.models import EvidenceItem

logger = logging.getLogger(__name__)

_NUMERIC_PATTERN = re.compile(r"(?<!\d)\d+(?:\.\d+)?(?!\d)")
_CATEGORICAL_PAIRS: tuple[tuple[str, str], ...] = (
    ("daily", "weekly"),
    ("weekly", "monthly"),
    ("daily", "monthly"),
    ("yes", "no"),
    ("true", "false"),
    ("enabled", "disabled"),
)
_WINDOW_CHARS = 100


class EntityTagConflictDetector(IConflictDetector):
    async def detect(
        self,
        items: list[EvidenceItem],
        config: ContextBuilderConfig,
    ) -> list[ConflictGroup]:
        _ = config
        try:
            tag_index: dict[str, list[EvidenceItem]] = defaultdict(list)
            for item in items:
                for tag in item.entity_tags:
                    tag_index[tag].append(item)

            groups: dict[tuple[str, str], set[str]] = defaultdict(set)

            for tag, tagged_items in tag_index.items():
                if len(tagged_items) < 2:
                    continue

                numeric_by_item: dict[str, set[str]] = {}
                for item in tagged_items:
                    numeric_by_item[item.item_id] = _extract_numeric_values(
                        item.text, tag
                    )

                all_numeric: set[str] = set()
                for values in numeric_by_item.values():
                    all_numeric.update(values)
                if len(all_numeric) > 1:
                    key = (tag, f"{tag}:numeric")
                    groups[key].update(item.item_id for item in tagged_items)

                categorical_by_item: dict[str, set[str]] = {}
                for item in tagged_items:
                    categorical_by_item[item.item_id] = _extract_categorical_values(
                        item.text, tag
                    )

                conflict_found = False
                for item_a in tagged_items:
                    for item_b in tagged_items:
                        if item_a.item_id >= item_b.item_id:
                            continue
                        cats_a = categorical_by_item[item_a.item_id]
                        cats_b = categorical_by_item[item_b.item_id]
                        if _categorical_conflict(cats_a, cats_b):
                            conflict_found = True
                            break
                    if conflict_found:
                        break

                if conflict_found:
                    key = (tag, f"{tag}:categorical")
                    groups[key].update(item.item_id for item in tagged_items)

            result: list[ConflictGroup] = []
            for (entity_tag, attribute), item_ids in sorted(groups.items()):
                ids = sorted(item_ids)
                if len(ids) >= 2:
                    result.append(
                        ConflictGroup(
                            entity_tag=entity_tag,
                            attribute=attribute,
                            item_ids=ids,
                            resolution=None,
                        )
                    )
            return result
        except Exception as exc:
            logger.warning("Conflict detection failed: %s", exc)
            return []


def _extract_numeric_values(text: str, entity_tag: str) -> set[str]:
    values: set[str] = set()
    lower_text = text.lower()
    lower_tag = entity_tag.lower()
    start = 0
    while True:
        idx = lower_text.find(lower_tag, start)
        if idx == -1:
            break
        window_start = max(0, idx - _WINDOW_CHARS)
        window_end = min(len(text), idx + len(entity_tag) + _WINDOW_CHARS)
        window = text[window_start:window_end]
        values.update(_NUMERIC_PATTERN.findall(window))
        start = idx + len(entity_tag)
    return values


def _extract_categorical_values(text: str, entity_tag: str) -> set[str]:
    tokens: set[str] = set()
    lower_text = text.lower()
    lower_tag = entity_tag.lower()
    start = 0
    while True:
        idx = lower_text.find(lower_tag, start)
        if idx == -1:
            break
        window_start = max(0, idx - _WINDOW_CHARS)
        window_end = min(len(text), idx + len(entity_tag) + _WINDOW_CHARS)
        window = lower_text[window_start:window_end]
        for token in re.findall(r"\b[a-z]+\b", window):
            tokens.add(token)
        start = idx + len(entity_tag)
    return tokens


def _categorical_conflict(a: set[str], b: set[str]) -> bool:
    for left, right in _CATEGORICAL_PAIRS:
        if (left in a and right in b) or (right in a and left in b):
            return True
    return False

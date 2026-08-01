"""Symptom taxonomy mapper — controlled many-to-many AR/EN normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from fields.pharmacy.recommend_pack import load_symptom_taxonomy


def _norm(text: str) -> str:
    t = (text or "").strip().casefold()
    t = re.sub(r"\s+", " ", t)
    return t


@dataclass
class TaxonomyMatch:
    node_ids: list[str] = field(default_factory=list)
    indication_tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    ambiguity_group: str | None = None
    clarification_prompt: str | None = None
    matched_labels: list[str] = field(default_factory=list)


class TaxonomyMapper:
    def __init__(self, taxonomy: dict[str, Any] | None = None) -> None:
        self._taxonomy = taxonomy or load_symptom_taxonomy()
        self._nodes = list(self._taxonomy.get("nodes") or [])

    def map_query(self, query: str) -> TaxonomyMatch:
        q = _norm(query)
        if not q:
            return TaxonomyMatch()

        hits: list[dict[str, Any]] = []
        matched_labels: list[str] = []
        for node in self._nodes:
            labels = (
                list(node.get("labels_en") or [])
                + list(node.get("labels_ar") or [])
                + list(node.get("synonyms") or [])
            )
            for label in labels:
                ln = _norm(str(label))
                if not ln:
                    continue
                if ln in q or (len(ln) >= 4 and q in ln):
                    hits.append(node)
                    matched_labels.append(str(label))
                    break

        if not hits:
            # Need-phrasing without exact node: light heuristic for recommend cues
            if any(
                k in q
                for k in (
                    "دواء ل",
                    "دوا ل",
                    "medicine for",
                    "something for",
                    "drug for",
                    "علاج ل",
                )
            ):
                return TaxonomyMatch(confidence=0.35)

        # Deduplicate nodes
        by_id: dict[str, dict[str, Any]] = {}
        for node in hits:
            nid = str(node.get("node_id") or "")
            if nid:
                by_id[nid] = node

        node_ids = list(by_id.keys())
        tags: list[str] = []
        ambiguity = None
        clarify = None
        for node in by_id.values():
            for tag in node.get("indication_tags") or []:
                t = str(tag)
                if t and t not in tags:
                    tags.append(t)
            ag = node.get("ambiguity_group")
            if ag:
                ambiguity = str(ag)
                clarify = node.get("clarification_prompt")

        # Multi-bucket without shared parent → lower confidence / ambiguity
        confidence = 0.0
        if node_ids:
            confidence = min(1.0, 0.55 + 0.15 * len(node_ids))
        if ambiguity and len(node_ids) >= 1:
            confidence = min(confidence, 0.45)

        return TaxonomyMatch(
            node_ids=node_ids,
            indication_tags=tags,
            confidence=confidence,
            ambiguity_group=ambiguity,
            clarification_prompt=str(clarify) if clarify else None,
            matched_labels=matched_labels,
        )


def map_need(query: str) -> TaxonomyMatch:
    return TaxonomyMapper().map_query(query)

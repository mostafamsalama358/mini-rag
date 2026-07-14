"""Rule-based KnowledgeNormalizer (research R4)."""

from __future__ import annotations

import logging
import re
from collections import OrderedDict

from core.knowledge.interfaces import KnowledgeNormalizer
from core.knowledge.models import (
    KnowledgeExtractionConfig,
    KnowledgeUnit,
    KnowledgeUnitMetadata,
    utc_now_iso,
)

logger = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def surface_key(text: str) -> str:
    normalized = text.lower().strip()
    normalized = _PUNCT_RE.sub("", normalized)
    return _WS_RE.sub(" ", normalized)


class RuleBasedKnowledgeNormalizer(KnowledgeNormalizer):
    """Three-pass surface / alias / exact-match deduplication."""

    @property
    def strategy_id(self) -> str:
        return "rule_based"

    def normalize(
        self,
        units: list[KnowledgeUnit],
        config: KnowledgeExtractionConfig,
    ) -> list[KnowledgeUnit]:
        alias_map_raw = (config.normalizer_params or {}).get("alias_map") or {}
        alias_map = {
            surface_key(str(k)): surface_key(str(v)) for k, v in alias_map_raw.items()
        }

        groups: OrderedDict[str, list[KnowledgeUnit]] = OrderedDict()
        alias_resolutions = 0
        for unit in units:
            text = str(
                unit.semantic_content.get("text")
                or unit.attributes.get("source_surface_form")
                or ""
            )
            key = surface_key(text)
            if key in alias_map:
                key = alias_map[key]
                alias_resolutions += 1
            groups.setdefault(key, []).append(unit)

        output: list[KnowledgeUnit] = []
        merged_count = 0
        for key, group in groups.items():
            canonical = group[0]
            if len(group) == 1:
                output.append(
                    KnowledgeUnit(
                        type=canonical.type,
                        semantic_content=dict(canonical.semantic_content),
                        participants=canonical.participants,
                        attributes=dict(canonical.attributes),
                        evidence_references=canonical.evidence_references,
                        relationships=canonical.relationships,
                        metadata=KnowledgeUnitMetadata(
                            extractor_strategy_id=canonical.metadata.extractor_strategy_id,
                            normalization_status="normalized",
                            created_at=utc_now_iso(),
                            config_hash=canonical.metadata.config_hash,
                        ),
                    )
                )
                continue

            merged_refs = []
            seen_ids: set[str] = set()
            aliases: list[str] = []
            for unit in group:
                for ref in unit.evidence_references:
                    if ref.id not in seen_ids:
                        seen_ids.add(ref.id)
                        merged_refs.append(ref)
                surface = str(unit.attributes.get("source_surface_form") or "")
                if surface and surface not in aliases:
                    aliases.append(surface)

            attrs = dict(canonical.attributes)
            if aliases:
                attrs["aliases"] = aliases
            semantic = dict(canonical.semantic_content)
            semantic["canonical_form"] = key

            output.append(
                KnowledgeUnit(
                    type=canonical.type,
                    semantic_content=semantic,
                    participants=canonical.participants,
                    attributes=attrs,
                    evidence_references=tuple(merged_refs),
                    relationships=(),
                    metadata=KnowledgeUnitMetadata(
                        extractor_strategy_id=canonical.metadata.extractor_strategy_id,
                        normalization_status="merged",
                        created_at=utc_now_iso(),
                        config_hash=canonical.metadata.config_hash,
                    ),
                )
            )
            merged_count += len(group) - 1

        logger.info(
            "knowledge_normalization merged_count=%s alias_resolutions=%s "
            "dedup_count=%s normalizer_strategy_id=%s",
            merged_count,
            alias_resolutions,
            merged_count,
            self.strategy_id,
        )
        return output

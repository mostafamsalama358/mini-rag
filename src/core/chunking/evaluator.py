"""Semantic Boundary Evaluator — computes BoundaryFeatures for adjacent element pairs."""

from __future__ import annotations

from core.chunking.models import BoundaryCandidate, BoundaryFeatures, ChunkingStrategyConfig
from core.document_intelligence.model import StructuralElement
from fields.schemas import ElementChunkConfig

_COMPATIBILITY_GROUPS: dict[str, frozenset[str]] = {
    "A": frozenset({"paragraph", "heading", "section", "list", "list-item", "quote"}),
    "B": frozenset({"table", "table-row"}),
    "C": frozenset({"code-block"}),
    "D": frozenset({"figure-placeholder"}),
}

_SECTION_TYPES = frozenset({"section", "heading"})


def _group_for_type(element_type: str) -> str | None:
    for group_id, members in _COMPATIBILITY_GROUPS.items():
        if element_type in members:
            return group_id
    return "A"


def _config_for(
    element_type: str,
    config: ChunkingStrategyConfig,
) -> ElementChunkConfig:
    if element_type in config.element_mapping:
        cfg = config.element_mapping[element_type]
        if cfg.max_chunk_chars is None:
            return cfg.model_copy(update={"max_chunk_chars": config.max_chars})
        return cfg
    defaults: dict[str, bool] = {
        "paragraph": True,
        "list-item": True,
        "table-row": False,
        "section": False,
        "table": False,
        "list": False,
        "heading": False,
        "code-block": False,
        "quote": False,
        "figure-placeholder": False,
    }
    return ElementChunkConfig(
        group=defaults.get(element_type, False),
        max_chunk_chars=config.max_chars,
        metadata_keys=[],
    )


def _ancestor_section_id(
    element: StructuralElement,
    element_by_id: dict[str, StructuralElement],
) -> str | None:
    current: StructuralElement | None = element
    visited: set[str] = set()
    while current is not None:
        if current.type in _SECTION_TYPES:
            return current.id
        parent_id = current.parent_id
        if not parent_id or parent_id in visited:
            return None
        visited.add(parent_id)
        current = element_by_id.get(parent_id)
    return None


class SemanticBoundaryEvaluator:
    """Computes all eleven BoundaryFeatures fields deterministically (research R8)."""

    def evaluate(
        self,
        candidate: BoundaryCandidate,
        context: dict,
    ) -> BoundaryFeatures:
        elements: list[StructuralElement] = context["elements"]
        element_by_id: dict[str, StructuralElement] = context["element_by_id"]
        config: ChunkingStrategyConfig = context["config"]

        left = element_by_id[candidate.left_element_id]
        right = element_by_id[candidate.right_element_id]

        element_section: dict[str, str | None] = context.get("element_section", {})

        hierarchy_continuity = candidate.left_parent_id == candidate.right_parent_id

        right_is_section = right.type in _SECTION_TYPES
        heading_continuity = not right_is_section

        left_section = element_section.get(left.id) or _ancestor_section_id(left, element_by_id)
        right_section = element_section.get(right.id) or _ancestor_section_id(right, element_by_id)
        section_continuity = left_section == right_section

        left_group = _group_for_type(candidate.left_type)
        right_group = _group_for_type(candidate.right_type)
        structural_compatibility = left_group == right_group

        incompatible_pairs = {
            ("code-block", "paragraph"),
            ("paragraph", "code-block"),
            ("figure-placeholder", "paragraph"),
            ("paragraph", "figure-placeholder"),
        }
        lexical_continuity = (candidate.left_type, candidate.right_type) not in incompatible_pairs

        table_integrity = True
        if candidate.left_type == "table-row" and candidate.right_type == "table-row":
            table_integrity = False
        elif candidate.left_type == "table-row" or candidate.right_type == "table-row":
            left_parent = left.parent_id
            right_parent = right.parent_id
            if candidate.left_type == "table-row" and candidate.right_type == "table-row":
                table_integrity = left_parent == right_parent
            elif candidate.left_type == "table-row":
                table_integrity = candidate.right_type == "table" and right.id == left_parent
            elif candidate.right_type == "table-row":
                table_integrity = candidate.left_type == "table" and left.id == right_parent
            else:
                table_integrity = True

        list_integrity = True
        if candidate.left_type == "list-item" or candidate.right_type == "list-item":
            if candidate.left_type == "list-item" and candidate.right_type == "list-item":
                list_integrity = left.parent_id == right.parent_id
            else:
                list_integrity = True

        code_integrity = not (
            (candidate.left_type == "code-block" and candidate.right_type != "code-block")
            or (candidate.right_type == "code-block" and candidate.left_type != "code-block")
        )

        quote_integrity = not (
            (candidate.left_type == "quote" and candidate.right_type != "quote")
            or (candidate.right_type == "quote" and candidate.left_type != "quote")
        )

        left_page = (left.provenance or {}).get("page")
        right_page = (right.provenance or {}).get("page")
        if left_page is None or right_page is None:
            layout_continuity = True
        else:
            try:
                layout_continuity = abs(int(left_page) - int(right_page)) <= 1
            except (TypeError, ValueError):
                layout_continuity = True

        separator = "\n" if candidate.accumulated_char_count > 0 else ""
        combined = candidate.accumulated_char_count + len(separator) + candidate.right_char_count
        size_budget: str = "within_limit" if combined <= config.max_chars else "over_limit"

        left_cfg = _config_for(candidate.left_type, config)
        right_cfg = _config_for(candidate.right_type, config)
        if not right_cfg.group and candidate.left_type == candidate.right_type:
            structural_compatibility = False
        if not left_cfg.group and candidate.left_type == candidate.right_type:
            structural_compatibility = False

        return BoundaryFeatures.model_construct(
            hierarchy_continuity=hierarchy_continuity,
            heading_continuity=heading_continuity,
            section_continuity=section_continuity,
            structural_compatibility=structural_compatibility,
            lexical_continuity=lexical_continuity,
            table_integrity=table_integrity,
            list_integrity=list_integrity,
            code_integrity=code_integrity,
            quote_integrity=quote_integrity,
            layout_continuity=layout_continuity,
            size_budget=size_budget,
        )

    def evaluate_fast(
        self,
        *,
        left: StructuralElement,
        right: StructuralElement,
        left_type: str,
        right_type: str,
        left_parent_id: str | None,
        right_parent_id: str | None,
        accumulated_char_count: int,
        right_char_count: int,
        context: dict,
    ):
        """Return lightweight FeatureFlags without allocating BoundaryFeatures."""
        from core.chunking.policy_fast import FeatureFlags

        element_by_id: dict[str, StructuralElement] = context["element_by_id"]
        config: ChunkingStrategyConfig = context["config"]
        element_section: dict[str, str | None] = context.get("element_section", {})

        hierarchy_continuity = left_parent_id == right_parent_id
        heading_continuity = right.type not in _SECTION_TYPES
        left_section = element_section.get(left.id) or _ancestor_section_id(left, element_by_id)
        right_section = element_section.get(right.id) or _ancestor_section_id(right, element_by_id)
        section_continuity = left_section == right_section

        left_group = _group_for_type(left_type)
        right_group = _group_for_type(right_type)
        structural_compatibility = left_group == right_group

        incompatible_pairs = {
            ("code-block", "paragraph"),
            ("paragraph", "code-block"),
            ("figure-placeholder", "paragraph"),
            ("paragraph", "figure-placeholder"),
        }
        lexical_continuity = (left_type, right_type) not in incompatible_pairs

        table_integrity = True
        if left_type == "table-row" and right_type == "table-row":
            table_integrity = False
        elif left_type == "table-row" or right_type == "table-row":
            if left_type == "table-row":
                table_integrity = right_type == "table" and right.id == left.parent_id
            elif right_type == "table-row":
                table_integrity = left_type == "table" and left.id == right.parent_id

        list_integrity = True
        if left_type == "list-item" and right_type == "list-item":
            list_integrity = left.parent_id == right.parent_id

        code_integrity = not (
            (left_type == "code-block" and right_type != "code-block")
            or (right_type == "code-block" and left_type != "code-block")
        )
        quote_integrity = not (
            (left_type == "quote" and right_type != "quote")
            or (right_type == "quote" and left_type != "quote")
        )

        left_page = (left.provenance or {}).get("page")
        right_page = (right.provenance or {}).get("page")
        if left_page is None or right_page is None:
            layout_continuity = True
        else:
            try:
                layout_continuity = abs(int(left_page) - int(right_page)) <= 1
            except (TypeError, ValueError):
                layout_continuity = True

        separator = "\n" if accumulated_char_count > 0 else ""
        combined = accumulated_char_count + len(separator) + right_char_count
        size_budget = "within_limit" if combined <= config.max_chars else "over_limit"

        left_cfg = _config_for(left_type, config)
        right_cfg = _config_for(right_type, config)
        if not right_cfg.group and left_type == right_type:
            structural_compatibility = False
        if not left_cfg.group and left_type == right_type:
            structural_compatibility = False

        return FeatureFlags(
            hierarchy_continuity=hierarchy_continuity,
            heading_continuity=heading_continuity,
            section_continuity=section_continuity,
            structural_compatibility=structural_compatibility,
            lexical_continuity=lexical_continuity,
            table_integrity=table_integrity,
            list_integrity=list_integrity,
            code_integrity=code_integrity,
            quote_integrity=quote_integrity,
            layout_continuity=layout_continuity,
            size_budget=size_budget,
        )

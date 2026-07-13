"""Fast boundary decision from precomputed feature flags."""

from __future__ import annotations

from typing import NamedTuple

from core.chunking.models import BoundaryDecision


class FeatureFlags(NamedTuple):
    hierarchy_continuity: bool
    heading_continuity: bool
    section_continuity: bool
    structural_compatibility: bool
    lexical_continuity: bool
    table_integrity: bool
    list_integrity: bool
    code_integrity: bool
    quote_integrity: bool
    layout_continuity: bool
    size_budget: str


def decide_fast(flags: FeatureFlags) -> BoundaryDecision:
    """Rule precedence without intermediate Pydantic models (research R1)."""
    if not flags.table_integrity or not flags.code_integrity or not flags.quote_integrity:
        triggered = [
            name
            for name, ok in (
                ("table_integrity", flags.table_integrity),
                ("code_integrity", flags.code_integrity),
                ("quote_integrity", flags.quote_integrity),
            )
            if not ok
        ]
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="structural_integrity",
            triggered_features=triggered,
            rationale="Structural integrity requires atomic table/code/quote units",
        )

    if not flags.section_continuity:
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="section_boundary",
            triggered_features=["section_continuity"],
            rationale="Elements belong to different sections",
        )

    if not flags.heading_continuity and flags.size_budget == "within_limit":
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="heading_boundary",
            triggered_features=["heading_continuity", "size_budget"],
            rationale="New heading boundary within size budget",
        )

    if not flags.hierarchy_continuity:
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="hierarchy_breach",
            triggered_features=["hierarchy_continuity"],
            rationale="Elements have different structural parents",
        )

    if flags.size_budget == "over_limit":
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="size_budget",
            triggered_features=["size_budget"],
            rationale="Merged chunk would exceed max_chars",
        )

    if not flags.structural_compatibility:
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="type_incompatibility",
            triggered_features=["structural_compatibility"],
            rationale="Element types are structurally incompatible",
        )

    if not flags.layout_continuity and not flags.lexical_continuity:
        return BoundaryDecision.model_construct(
            decision="split",
            applied_rule="layout_lexical_incompatibility",
            triggered_features=["layout_continuity", "lexical_continuity"],
            rationale="Layout and lexical continuity both failed",
        )

    return BoundaryDecision.model_construct(
        decision="merge",
        applied_rule="default_merge",
        triggered_features=["size_budget"],
        rationale="All boundary signals pass; merge elements",
    )

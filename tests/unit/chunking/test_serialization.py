"""US6/SC-013: BoundaryFeatures and BoundaryDecision JSON round-trip."""

from __future__ import annotations

import json

from core.chunking.models import BoundaryDecision, BoundaryFeatures


def test_boundary_features_round_trip():
    features = BoundaryFeatures(
        hierarchy_continuity=True,
        heading_continuity=False,
        section_continuity=True,
        structural_compatibility=True,
        lexical_continuity=True,
        table_integrity=True,
        list_integrity=True,
        code_integrity=True,
        quote_integrity=True,
        layout_continuity=True,
        size_budget="within_limit",
    )
    restored = BoundaryFeatures.model_validate(
        json.loads(json.dumps(features.model_dump()))
    )
    assert restored == features


def test_boundary_decision_round_trip():
    decision = BoundaryDecision(
        decision="split",
        applied_rule="section_boundary",
        triggered_features=["section_continuity"],
        rationale="Different sections",
    )
    restored = BoundaryDecision.model_validate(
        json.loads(json.dumps(decision.model_dump()))
    )
    assert restored == decision

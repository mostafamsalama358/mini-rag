"""Default semantic-structural chunking strategy and rule-based boundary policy."""

from __future__ import annotations

from core.chunking.builder import ChunkBuilder, _render_element
from core.chunking.evaluator import SemanticBoundaryEvaluator
from core.chunking.interfaces import ChunkingStrategy
from core.chunking.models import (
    BoundaryCandidate,
    BoundaryDecision,
    BoundaryFeatures,
    ChunkingStrategyConfig,
    ChunkSet,
    ValidationReport,
)
from core.chunking.policy_fast import decide_fast
from core.chunking.registry import get_boundary_decision_policy
from core.chunking.validator import ChunkValidator
from core.document_intelligence.model import DocumentModel


class RuleBasedBoundaryDecisionPolicy:
    """Deterministic seven-level rule precedence (research R1)."""

    def decide(
        self,
        candidate: BoundaryCandidate,
        features: BoundaryFeatures,
    ) -> BoundaryDecision:
        if not features.table_integrity or not features.code_integrity or not features.quote_integrity:
            triggered = [
                name
                for name, ok in (
                    ("table_integrity", features.table_integrity),
                    ("code_integrity", features.code_integrity),
                    ("quote_integrity", features.quote_integrity),
                )
                if not ok
            ]
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="structural_integrity",
                triggered_features=triggered,
                rationale="Structural integrity requires atomic table/code/quote units",
            )

        if not features.section_continuity:
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="section_boundary",
                triggered_features=["section_continuity"],
                rationale="Elements belong to different sections",
            )

        if not features.heading_continuity and features.size_budget == "within_limit":
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="heading_boundary",
                triggered_features=["heading_continuity", "size_budget"],
                rationale="New heading boundary within size budget",
            )

        if not features.hierarchy_continuity:
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="hierarchy_breach",
                triggered_features=["hierarchy_continuity"],
                rationale="Elements have different structural parents",
            )

        if features.size_budget == "over_limit":
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="size_budget",
                triggered_features=["size_budget"],
                rationale="Merged chunk would exceed max_chars",
            )

        if not features.structural_compatibility:
            return BoundaryDecision.model_construct(
                decision="split",
                applied_rule="type_incompatibility",
                triggered_features=["structural_compatibility"],
                rationale="Element types are structurally incompatible",
            )

        if not features.layout_continuity and not features.lexical_continuity:
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


_SECTION_TYPES = frozenset({"section", "heading"})


def _build_element_section_map(elements: list) -> dict[str, str | None]:
    active_section: str | None = None
    mapping: dict[str, str | None] = {}
    for element in elements:
        if element.type in _SECTION_TYPES:
            active_section = element.id
        mapping[element.id] = active_section
    return mapping


class SemanticStructuralChunkingStrategy(ChunkingStrategy):
    """Boundary Decision Pipeline orchestrator."""

    def __init__(self, config: ChunkingStrategyConfig | None = None) -> None:
        self._config = config or ChunkingStrategyConfig()
        self._evaluator = SemanticBoundaryEvaluator()

    @property
    def strategy_id(self) -> str:
        return "semantic_structural"

    def chunk(self, document_model: DocumentModel, config: ChunkingStrategyConfig) -> ChunkSet:
        elements = list(document_model.elements)
        if not elements:
            empty_report = ValidationReport(status="pass")
            return ChunkSet(
                chunks=[],
                validation_report=empty_report,
                asset_id=str(document_model.asset_id),
                strategy_id=self.strategy_id,
                element_counts_by_type={},
            )

        element_by_id = {el.id: el for el in elements}
        element_section = _build_element_section_map(elements)
        rendered_text = {el.id: _render_element(el) for el in elements}
        context = {
            "elements": elements,
            "element_by_id": element_by_id,
            "element_section": element_section,
            "rendered_text": rendered_text,
            "config": config,
        }
        policy = get_boundary_decision_policy(config.policy)
        use_fast_policy = config.policy == "rule_based"
        builder = ChunkBuilder(
            document_model,
            config,
            self.strategy_id,
            file_name=(elements[0].provenance or {}).get("file_name"),
        )

        builder.open_chunk(elements[0])
        accumulated = len(rendered_text[elements[0].id])

        for idx in range(1, len(elements)):
            left = elements[idx - 1]
            right = elements[idx]
            right_rendered = rendered_text[right.id]
            if use_fast_policy:
                flags = self._evaluator.evaluate_fast(
                    left=left,
                    right=right,
                    left_type=left.type,
                    right_type=right.type,
                    left_parent_id=left.parent_id,
                    right_parent_id=right.parent_id,
                    accumulated_char_count=accumulated,
                    right_char_count=len(right_rendered),
                    context=context,
                )
                decision = decide_fast(flags)
            else:
                candidate = BoundaryCandidate.model_construct(
                    left_element_id=left.id,
                    right_element_id=right.id,
                    left_type=left.type,
                    right_type=right.type,
                    left_parent_id=left.parent_id,
                    right_parent_id=right.parent_id,
                    accumulated_char_count=accumulated,
                    right_char_count=len(right_rendered),
                )
                features = self._evaluator.evaluate(candidate, context)
                decision = policy.decide(candidate, features)

            if decision.decision == "merge":
                builder.append_element(right, decision)
                accumulated += len(right_rendered) + (1 if accumulated > 0 else 0)
            else:
                builder.close_chunk(decision)
                builder.open_chunk(right)
                accumulated = len(right_rendered)

        builder.close_chunk(
            BoundaryDecision(
                decision="split",
                applied_rule="end_of_document",
                triggered_features=["size_budget"],
                rationale="Final chunk close at end of document",
            )
        )
        chunks = builder.finalize()
        report = ChunkValidator(config).validate(chunks)

        return ChunkSet(
            chunks=chunks,
            validation_report=report,
            asset_id=str(document_model.asset_id),
            strategy_id=self.strategy_id,
            element_counts_by_type=document_model.element_counts(),
        )

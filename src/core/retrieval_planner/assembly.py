"""Plan assembly helpers — constraints, hints, output shape, and PlanAssembler."""

from __future__ import annotations

from datetime import datetime, timezone

from core.retrieval_planner.models import (
    PLANNER_VERSION,
    SCHEMA_VERSION,
    ExecutionHints,
    OutputShape,
    OutputShapeType,
    PlannerDiagnostics,
    QueryFilter,
    QueryIntent,
    ResolvedEntity,
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalPlan,
    RetrievalPlanMetadata,
    RetrievalPlannerConfig,
    StrategyType,
    compute_config_hash,
    compute_plan_id,
)

_INTENT_TO_SHAPE: dict[str, tuple[OutputShapeType, int | None, bool]] = {
    "factual": ("single_fact", None, False),
    "list": ("list", None, True),
    "comparative": ("comparison", None, False),
    "procedural": ("narrative", None, False),
    "tabular": ("table", None, True),
    "navigational": ("single_fact", 1, False),
    "mixed": ("summary", None, False),
}


class ConstraintsBuilder:
    @staticmethod
    def build(
        filters: list[QueryFilter],
        config: RetrievalPlannerConfig,
    ) -> RetrievalConstraints:
        language: str | None = None
        freshness: str | None = None
        for f in filters:
            if f.filter_type == "language" and f.source == "implicit":
                language = str(f.value) if f.value is not None else None
            if f.filter_type == "date" and freshness is None:
                # Use ISO duration if filter value looks like one, else leave None
                val = str(f.value) if f.value is not None else ""
                if val.startswith("P"):
                    freshness = val

        return RetrievalConstraints(
            latency_budget_ms=config.default_latency_budget_ms,
            cost_budget=config.default_cost_budget,
            freshness_window=freshness,
            required_language=language,
            citation_required=config.citation_required,
        )


class HintsBuilder:
    @staticmethod
    def build(
        intent: QueryIntent,
        entities: list[ResolvedEntity],
        constraints: RetrievalConstraints,
    ) -> ExecutionHints | None:
        hints = ExecutionHints()
        triggered = False

        if intent.category == "tabular":
            hints.allow_table_search = True
            triggered = True

        doc_types = [
            e.canonical_form for e in entities if e.entity_type == "document"
        ]
        if doc_types:
            hints.preferred_document_types = doc_types
            triggered = True

        section_kinds = [
            e.canonical_form for e in entities if e.entity_type == "section"
        ]
        if section_kinds:
            hints.preferred_section_kinds = section_kinds
            triggered = True

        if intent.category in ("comparative", "mixed"):
            hints.expand_entities = True
            triggered = True

        if constraints.freshness_window is not None:
            hints.prioritize_recent_content = True
            triggered = True

        return hints if triggered else None


class OutputShapeDeriver:
    @staticmethod
    def derive(intent: QueryIntent) -> OutputShape:
        shape_type, max_items, structured = _INTENT_TO_SHAPE.get(
            intent.category, ("narrative", None, False)
        )
        return OutputShape(
            shape_type=shape_type,
            max_items=max_items,
            structured=structured,
        )


class PlanAssembler:
    def assemble(
        self,
        *,
        canonical_query: str,
        intent: QueryIntent,
        entities: list[ResolvedEntity],
        filters: list[QueryFilter],
        strategies: list[StrategyType],
        limits: RetrievalLimits,
        clarification_required: bool,
        clarification_question: str | None,
        planner_confidence: float,
        config: RetrievalPlannerConfig,
        diagnostics: PlannerDiagnostics | None = None,
        created_at: str | None = None,
    ) -> RetrievalPlan:
        constraints = ConstraintsBuilder.build(filters, config)
        hints = HintsBuilder.build(intent, entities, constraints)
        output_shape = OutputShapeDeriver.derive(intent)

        if not config.diagnostics_enabled:
            diagnostics = None

        config_hash = compute_config_hash(config)
        plan_id = compute_plan_id(
            canonical_query,
            intent.category,
            strategies,
            config_hash,
        )
        # Deterministic created_at for id stability tests — use fixed epoch when testing;
        # plan_id itself does not include timestamp (research R4).
        ts = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return RetrievalPlan(
            canonical_query=canonical_query,
            intent=intent,
            entities=tuple(entities),
            filters=tuple(filters),
            retrieval_strategies=tuple(strategies),
            retrieval_limits=limits,
            retrieval_constraints=constraints,
            execution_hints=hints,
            output_shape=output_shape,
            clarification_required=clarification_required,
            clarification_question=clarification_question,
            planner_confidence=planner_confidence,
            diagnostics=diagnostics,
            metadata=RetrievalPlanMetadata(
                plan_id=plan_id,
                planner_version=PLANNER_VERSION,
                schema_version=SCHEMA_VERSION,
                config_hash=config_hash,
                created_at=ts,
            ),
        )

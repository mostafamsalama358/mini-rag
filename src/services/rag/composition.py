"""Composition root for the unified RAG pipeline (spec 015)."""

from __future__ import annotations

import logging
from typing import Any

from core.answer_generation.registry import AnswerGenerationRegistry
from core.context_builder.registry import ContextBuilderRegistry
from core.evidence_orchestrator.registry import EvidenceOrchestratorRegistry
from core.retrieval_engine.expansion.entity_hint import EntityHintExpander
from core.retrieval_engine.fusion.rrf import RRFScoreFuser
from core.retrieval_engine.interfaces import IRetriever
from core.retrieval_engine.registry import RetrieverRegistry
from core.retrieval_engine.reranking.passthrough import PassthroughReranker
from core.retrieval_planner.registry import RetrievalPlannerRegistry
from helpers.config import Settings, get_settings
from services.rag.adapters.chunk_reader import SqlChunkReader
from services.rag.adapters.embedding_provider import EmbeddingProviderAdapter
from services.rag.adapters.field_context import FieldContextAdapter
from services.rag.adapters.interaction_retriever import StructuredInteractionRetriever
from services.rag.adapters.reranker_adapter import LegacyRerankerAdapter
from services.rag.adapters.sparse_retriever import PgVectorSparseRetriever
from services.rag.adapters.vector_retriever import PgVectorDenseRetriever
from services.rag.answer_service import RAGService
from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.query_parse_service import QueryParseService
from services.rag.pipeline.response_adapter import ResponseAdapter
from services.rag.pipeline.router import PipelineRouter
from services.rag.pipeline.shadow_runner import ShadowRunner
from services.rag.pipeline.shadow_store import ShadowComparisonStore
from services.rag.pipeline.skill_orchestrator import SkillRuntimeOrchestrator
from services.rag.pipeline.unified_orchestrator import UnifiedRagOrchestrator
from services.rag.rag_service import NLPController

logger = logging.getLogger("uvicorn.error")

# Strategies that must be present when mode is shadow/unified (adapter capabilities).
_REQUIRED_ADAPTER_STRATEGIES = (
    "dense",
    "sparse",
    # Field-pack defaults still emit semantic/keyword — aliases required.
    "semantic",
    "keyword",
)


class _StrategyAliasRetriever(IRetriever):
    """Re-register an adapter under an alternate strategy id (semantic↔dense)."""

    def __init__(self, inner: IRetriever, strategy: str) -> None:
        self._inner = inner
        self._strategy = strategy

    @property
    def retriever_id(self) -> str:
        return self._inner.retriever_id

    @property
    def supported_strategy(self) -> str:
        return self._strategy

    @property
    def sequential_only(self) -> bool:
        return self._inner.sequential_only

    @property
    def experimental(self) -> bool:
        return self._inner.experimental

    async def retrieve(self, query, context):
        return await self._inner.retrieve(query, context)


class RagPipelineFactory:
    """Built once at startup; creates request-scoped routers."""

    def __init__(
        self,
        *,
        router_factory,
        settings: Settings | None = None,
    ) -> None:
        self._router_factory = router_factory
        self._settings = settings

    def create_router(self) -> PipelineRouter:
        return self._router_factory()


def _validate_capabilities(registry: RetrieverRegistry, *, mode: str) -> None:
    missing = [
        strategy
        for strategy in _REQUIRED_ADAPTER_STRATEGIES
        if registry.get_retriever(strategy) is None
    ]
    if missing:
        raise RuntimeError(
            f"RAG pipeline mode={mode!r} missing retriever capabilities for "
            f"strategies={missing}. Register PgVectorDense/Sparse adapters "
            f"(and semantic/keyword aliases) before startup."
        )


def _registered_strategies(registry: RetrieverRegistry) -> set[str]:
    """Strategies with a concrete retriever, plus hybrid (expanded at engine)."""
    found: set[str] = {"hybrid"}
    for strategy in (
        "dense",
        "sparse",
        "semantic",
        "keyword",
        "metadata",
        "document",
        "section",
        "table",
        "graph",
        "interaction",
        "structured",
    ):
        if registry.get_retriever(strategy) is not None:
            found.add(strategy)
    return found


def _align_planner_to_registry(
    planner_config,
    registry: RetrieverRegistry,
    *,
    mode: str,
):
    """Intersect planner available_strategies with registered retrievers.

    Fail fast when an advertised strategy cannot be executed — prevents silent
    zero-candidate plans (navigational→metadata/document with no retriever).
    """
    registered = _registered_strategies(registry)
    available = [s for s in planner_config.available_strategies if s in registered]
    if not available:
        raise RuntimeError(
            f"RAG pipeline mode={mode!r} planner has no available_strategies "
            f"overlapping registered retrievers={sorted(registered)}"
        )

    orphaned: list[str] = []
    for strategy in planner_config.available_strategies:
        if strategy not in registered:
            orphaned.append(strategy)
    if orphaned:
        logger.warning(
            "planner_strategies_not_registered mode=%s dropped=%s registered=%s",
            mode,
            orphaned,
            sorted(registered),
        )

    cleaned_mappings: dict[str, list[str]] = {}
    for intent, strats in planner_config.strategy_mappings.items():
        kept = [s for s in strats if s in available]
        cleaned_mappings[intent] = kept or [planner_config.default_strategy]

    default = planner_config.default_strategy
    if default not in available:
        default = "semantic" if "semantic" in available else available[0]

    return planner_config.model_copy(
        update={
            "available_strategies": available,
            "strategy_mappings": cleaned_mappings,
            "default_strategy": default,
        }
    )


def build_rag_pipeline_factory(app: Any) -> RagPipelineFactory:
    """Wire registries, adapters, and router factory from application singletons."""
    settings = get_settings()
    mode = str(getattr(settings, "RAG_PIPELINE_MODE", "legacy") or "legacy").strip().lower()

    vectordb = getattr(app, "vectordb_client", None)
    embedding = getattr(app, "embedding_client", None)
    generation = getattr(app, "generation_client", None)
    db_client = getattr(app, "db_client", None)
    field_registry = getattr(app, "field_registry", None)
    reranker = getattr(app, "reranker", None)
    template_parser = getattr(app, "template_parser", None)

    if mode in {"shadow", "unified"}:
        if vectordb is None:
            raise RuntimeError("vectordb_client required for shadow/unified pipeline")
        if embedding is None:
            raise RuntimeError("embedding_client required for shadow/unified pipeline")
        if generation is None:
            raise RuntimeError("generation_client required for shadow/unified pipeline")
        if field_registry is None:
            raise RuntimeError("field_registry required for shadow/unified pipeline")

    field_adapter = FieldContextAdapter()
    default_profile = None
    if field_registry is not None:
        try:
            default_profile = field_registry.build_profile(field_registry.default_key)
        except Exception as exc:
            logger.warning("field_profile_build_failed err=%s", exc)
            default_profile = None

    from core.retrieval_engine.models import RetrievalEngineConfig

    if default_profile is not None:
        try:
            engine_config = field_adapter.build_engine_config(default_profile)
        except Exception:
            engine_config = RetrievalEngineConfig()
    else:
        engine_config = RetrievalEngineConfig()

    rrf_k = int(getattr(settings, "RAG_RRF_K", None) or engine_config.rrf_k or 60)

    dense = PgVectorDenseRetriever(
        vectordb_client=vectordb,
        embedding_client=embedding,
    )
    sparse = PgVectorSparseRetriever(
        vectordb_client=vectordb,
        embedding_client=embedding,
    )
    interaction = StructuredInteractionRetriever(db_client=db_client)

    registry = RetrieverRegistry()
    registry.register_retriever(dense)
    registry.register_retriever(sparse)
    registry.register_retriever(interaction)
    # Field-pack / planner defaults still use semantic + keyword.
    registry.register_retriever(_StrategyAliasRetriever(dense, "semantic"))
    registry.register_retriever(_StrategyAliasRetriever(sparse, "keyword"))
    registry.register_expander(EntityHintExpander())
    registry.register_fuser(RRFScoreFuser(k=rrf_k))
    registry.register_reranker(PassthroughReranker())

    if reranker is not None and bool(getattr(settings, "RAG_ENABLE_RERANKER", False)):
        legacy_rerank = LegacyRerankerAdapter(reranker, reranker_id="legacy")
        registry.register_reranker(legacy_rerank)
        # Prefer legacy when enabled.
        engine_config = engine_config.model_copy(update={"reranker_backend": "legacy"})

    if mode in {"shadow", "unified"}:
        _validate_capabilities(registry, mode=mode)

    engine = registry.build_pipeline(engine_config)

    planner_registry = RetrievalPlannerRegistry()
    planner_registry.register_defaults()
    from core.retrieval_planner.models import RetrievalPlannerConfig

    if default_profile is not None:
        try:
            planner_config = field_adapter.build_planner_config(default_profile)
        except Exception:
            planner_config = RetrievalPlannerConfig()
    else:
        planner_config = RetrievalPlannerConfig()
    if mode in {"shadow", "unified"}:
        planner_config = _align_planner_to_registry(
            planner_config, registry, mode=mode
        )
    planner = planner_registry.build_pipeline(planner_config)

    embedding_provider = EmbeddingProviderAdapter(embedding) if embedding else None
    chunk_reader = SqlChunkReader(db_client=db_client)
    evidence_registry = EvidenceOrchestratorRegistry(
        chunk_reader=chunk_reader,
        embedding_provider=embedding_provider,
    )
    evidence_cfg = None
    if default_profile is not None:
        try:
            evidence_cfg = field_adapter.build_evidence_config(default_profile)
        except Exception:
            evidence_cfg = None
    evidence_orchestrator = evidence_registry.build_orchestrator(evidence_cfg)

    from core.context_builder.config import ContextBuilderConfig

    if default_profile is not None:
        try:
            context_config = field_adapter.build_context_config(default_profile)
        except Exception:
            context_config = ContextBuilderConfig()
    else:
        context_config = ContextBuilderConfig()
    context_builder = ContextBuilderRegistry.build(context_config)

    from core.answer_generation.config import AnswerGenerationConfig

    if default_profile is not None:
        try:
            answer_config = field_adapter.build_answer_config(default_profile)
        except Exception:
            answer_config = AnswerGenerationConfig(
                system_prompt_template=(
                    "Answer the question using the provided context."
                )
            )
    else:
        answer_config = AnswerGenerationConfig(
            system_prompt_template="Answer the question using the provided context."
        )
    answer_pipeline = AnswerGenerationRegistry.build(answer_config, generation)

    parse_service = QueryParseService(
        generation_client=generation,
        db_client=db_client,
    )
    unified = UnifiedRagOrchestrator(
        query_parse_service=parse_service,
        planner=planner,
        engine=engine,
        evidence_orchestrator=evidence_orchestrator,
        context_builder=context_builder,
        answer_pipeline=answer_pipeline,
        field_context_adapter=field_adapter,
        vectordb_client=vectordb,
        embedding_client=embedding,
        db_client=db_client,
    )

    nlp_controller = NLPController(
        vectordb_client=vectordb,
        generation_client=generation,
        embedding_client=embedding,
        template_parser=template_parser,
        reranker=reranker,
        field_registry=field_registry,
    )
    rag_service = RAGService(
        db_client=db_client,
        nlp_controller=nlp_controller,
        generation_client=generation,
        template_parser=template_parser,
        reranker=reranker,
        field_registry=field_registry,
    )
    legacy_executor = LegacyPipelineExecutor(rag_service=rag_service)
    response_adapter = ResponseAdapter()

    skill_runtime = SkillRuntimeOrchestrator(
        db_client=db_client,
        nlp_controller=nlp_controller,
        generation_client=generation,
        template_parser=template_parser,
        reranker=reranker,
        response_adapter=response_adapter,
    )
    rag_service.set_skill_runtime(skill_runtime)

    # ShadowRunner is US2 — dual-run with legacy-wins response.
    shadow_runner = ShadowRunner(
        legacy_executor=legacy_executor,
        unified_orchestrator=unified,
        response_adapter=response_adapter,
        store=ShadowComparisonStore(getattr(settings, "RAG_PIPELINE_SHADOW_DIR", ".rag_shadow/")),
        settings=settings,
    )

    def _create_router() -> PipelineRouter:
        return PipelineRouter(
            legacy_executor=legacy_executor,
            unified_orchestrator=unified,
            shadow_runner=shadow_runner,
            skill_runtime=skill_runtime,
            response_adapter=response_adapter,
            settings=settings,
        )

    return RagPipelineFactory(router_factory=_create_router, settings=settings)

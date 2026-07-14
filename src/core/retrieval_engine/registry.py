"""Registry mapping strategy / component ids to Retrieval Engine implementations."""

from __future__ import annotations

from core.retrieval_engine.errors import RetrieverNotFoundError
from core.retrieval_engine.interfaces import (
    IQueryExpander,
    IReranker,
    IRetriever,
    IScoreFuser,
)
from core.retrieval_engine.models import RetrievalEngineConfig
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_engine.router import StrategyRouter


class RetrieverRegistry:
    def __init__(self) -> None:
        self._retrievers: dict[str, IRetriever] = {}
        self._expanders: dict[str, IQueryExpander] = {}
        self._fusers: dict[str, IScoreFuser] = {}
        self._rerankers: dict[str, IReranker] = {}

    def register_retriever(self, impl: IRetriever) -> None:
        self._retrievers[impl.supported_strategy] = impl

    def register_expander(self, impl: IQueryExpander) -> None:
        self._expanders[impl.expander_id] = impl

    def register_fuser(self, impl: IScoreFuser) -> None:
        self._fusers[impl.fuser_id] = impl

    def register_reranker(self, impl: IReranker) -> None:
        self._rerankers[impl.reranker_id] = impl

    def get_retriever(self, strategy: str) -> IRetriever | None:
        return self._retrievers.get(strategy)

    def get_expander(self, expander_id: str) -> IQueryExpander:
        if expander_id not in self._expanders:
            raise RetrieverNotFoundError(f"unknown expander: {expander_id!r}")
        return self._expanders[expander_id]

    def get_fuser(self, fuser_id: str) -> IScoreFuser:
        if fuser_id not in self._fusers:
            raise RetrieverNotFoundError(f"unknown fuser: {fuser_id!r}")
        return self._fusers[fuser_id]

    def get_reranker(self, reranker_id: str) -> IReranker:
        if reranker_id not in self._rerankers:
            raise RetrieverNotFoundError(f"unknown reranker: {reranker_id!r}")
        return self._rerankers[reranker_id]

    def register_defaults(
        self,
        *,
        vector_store=None,
        fts_store=None,
        metadata_store=None,
        structured_store=None,
        rrf_k: int = 60,
    ) -> None:
        """Register built-in non-experimental implementations.

        GraphRetriever and SQLRetriever are experimental and must be registered
        explicitly by the build_pipeline caller when needed.
        """
        from core.retrieval_engine.expansion.passthrough import PassthroughExpander
        from core.retrieval_engine.fusion.rrf import RRFScoreFuser
        from core.retrieval_engine.reranking.passthrough import PassthroughReranker
        from core.retrieval_engine.retrievers.dense import DenseVectorRetriever
        from core.retrieval_engine.retrievers.metadata import MetadataRetriever
        from core.retrieval_engine.retrievers.sparse import SparseRetriever
        from core.retrieval_engine.retrievers.structured import StructuredRetriever

        self.register_retriever(DenseVectorRetriever(vector_store))
        self.register_retriever(SparseRetriever(fts_store))
        self.register_retriever(MetadataRetriever(metadata_store))
        self.register_retriever(StructuredRetriever(structured_store))
        self.register_expander(PassthroughExpander())
        self.register_fuser(RRFScoreFuser(k=rrf_k))
        self.register_reranker(PassthroughReranker())

    def build_pipeline(
        self,
        config: RetrievalEngineConfig,
        policy: ExecutionPolicy | None = None,
    ):
        from core.retrieval_engine.budget.enforcer import BudgetEnforcer
        from core.retrieval_engine.pipeline import RetrievalEnginePipeline
        from core.retrieval_engine.tracing.tracer import RetrievalTracer

        fusion_id = "rrf" if config.fusion_algorithm == "rrf" else config.fusion_algorithm
        expander = (
            list(self._expanders.values())[0]
            if self._expanders
            else self.get_expander("passthrough")
        )
        # Prefer passthrough expander unless only one is registered.
        if "passthrough" in self._expanders:
            expander = self._expanders["passthrough"]

        return RetrievalEnginePipeline(
            expander=expander,
            router=StrategyRouter(self.get_retriever),
            fuser=self.get_fuser(fusion_id if fusion_id in self._fusers else "rrf"),
            reranker=self.get_reranker(config.reranker_backend)
            if config.reranker_backend in self._rerankers
            else self.get_reranker("passthrough"),
            budget_enforcer=BudgetEnforcer(),
            tracer_factory=RetrievalTracer,
            config=config,
            default_policy=policy or ExecutionPolicy(),
        )


default_registry = RetrieverRegistry()

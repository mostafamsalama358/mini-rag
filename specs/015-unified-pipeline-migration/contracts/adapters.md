# Contract: Infrastructure Adapters

**Feature**: 015-unified-pipeline-migration | **Version**: 1.0.0

Maps existing production infrastructure to SpecKit core protocols. All adapters live in
`services/rag/adapters/`. Adapters MUST NOT import from `services/rag/answer_service.py`.

---

## Design Principles

1. **Inject clients, not globals** — receive `vectordb_client`, `embedding_client`, etc. via
   constructor.
2. **Project-scoped collection** — resolve `collection_{embedding_size}_{project_id}` per call.
3. **No business logic** — filtering/entity resolution inputs come from planner/engine context,
   not adapter-internal branches.
4. **Type mapping centralized** — use `type_mapping.py` for all cross-model conversions.

---

## Adapter Capability Declaration

Each retriever adapter MUST expose a static capability set used at factory startup for
fail-fast validation — not runtime discovery.

```python
@dataclass(frozen=True)
class AdapterCapabilities:
    retriever_id: str
    supported_strategy: str
    features: frozenset[str]  # e.g. {"scoped_search", "metadata_filter", "hybrid_sparse"}
```

**Standard feature tokens** (v1):

| Token | Meaning |
|-------|---------|
| `dense_vector` | Dense embedding search |
| `sparse_text` | FTS / keyword search |
| `scoped_search` | Entity prefix / field scoping |
| `metadata_filter` | Arbitrary metadata filter passthrough |
| `structured_interaction` | Domain structured lookup |

At startup, `build_rag_pipeline_factory` MUST verify every strategy listed in generic
field-pack defaults has a registered adapter with matching `supported_strategy`. Missing
capability → startup error with strategy name (not silent runtime no-op).

**Future extensibility**: New tokens and adapters are additive; no dynamic plugin protocol in
v1. Qdrant or new backends add new adapter classes + registry registration only.

---

## Retriever Adapters

### `PgVectorDenseRetriever` → `IRetriever`

| Property | Value |
|----------|-------|
| `retriever_id` | `"pgvector_dense"` |
| `supported_strategy` | `"dense"` |
| `sequential_only` | `false` |

```python
async def retrieve(
    self,
    query: RetrievalQuery,
    context: RetrievalContext,
) -> list[RawCandidate]:
    ...
```

**Maps**:

- `query.text` / embedding → `search_by_vector[_scoped]`
- Scoped params from `RetrievalContext.metadata` keys: `entity_key`, `entity_prefix`,
  `field_key`, `metadata_filter`
- Output: `RawCandidate` with `doc_id`, `chunk_id`, `score`, `text`, `metadata`

---

### `PgVectorSparseRetriever` → `IRetriever`

| Property | Value |
|----------|-------|
| `retriever_id` | `"pgvector_sparse"` |
| `supported_strategy` | `"sparse"` |

**Maps**: `search_by_text[_scoped]` paths when hybrid enabled.

---

### `StructuredInteractionRetriever` → `IRetriever`

| Property | Value |
|----------|-------|
| `retriever_id` | `"structured_interaction"` |
| `supported_strategy` | `"structured_interaction"` |

**Maps**: Existing `fetch_interaction_documents` logic; on miss returns empty list (engine
handles fallback strategy via planner).

**Domain config**: Enabled when field-pack declares `retrieval.strategies.interactions`.

---

## Fusion / Rerank Adapters

### `RrfScoreFuser` → `IScoreFuser`

Wrap existing `core.retrieval.hybrid_rrf` logic OR use engine's default RRF fuser if equivalent.
Must honor `RAG_RRF_K` from settings.

### `LegacyRerankerAdapter` → `IReranker`

```python
async def rerank(
    self,
    query_text: str,
    candidates: list[RawCandidate],
) -> list[RawCandidate]:
    # Convert → RetrievedDocument → utils.rerank → convert back
```

**Maps**: `app.reranker` from startup; respects `RAG_ENABLE_RERANKER`.

---

## Evidence Adapters

### `SqlChunkReader` → `IChunkReader`

```python
async def get_chunk(self, chunk_id: str, document_id: str) -> Chunk | None:
```

**Maps**: `ChunkModel` async repository; loads chunk text + metadata for evidence expansion.

### `EmbeddingProviderAdapter` → `IEmbeddingProvider`

```python
async def embed_texts(self, texts: list[str]) -> list[list[float]]:
```

**Maps**: `embedding_client.embed_text_async` with batching per settings.

---

## Field / Planner Context Adapter

### `FieldContextAdapter`

Not a core protocol; helper used by orchestrator to build planner/engine configs.

```python
def build_planner_config(profile: FieldProfile) -> RetrievalPlannerConfig: ...
def build_engine_policy(ctx: PipelineExecutionContext, profile: FieldProfile) -> ExecutionPolicy: ...
def build_evidence_config(profile: FieldProfile) -> EvidenceOrchestratorConfig: ...
def build_context_config(profile: FieldProfile) -> ContextBuilderConfig: ...
def build_answer_config(profile: FieldProfile) -> AnswerGenerationConfig: ...
```

**Source**: Field-pack YAML slices (`retrieval_planner`, `retrieval_engine`, etc.) merged with
generic defaults — same pattern as 014 `AnswerQualityConfig`.

---

## LLM Adapter

Answer generation already uses `LLMInterface` from `stores.llm`. **No new adapter** — inject
existing `app.generation_client` into `AnswerGenerationPipeline` at factory time.

---

## Type Mapping Module

### `type_mapping.py` (required functions)

```python
def retrieved_document_to_raw_candidate(doc: RetrievedDocument) -> RawCandidate: ...
def raw_candidate_to_retrieved_document(c: RawCandidate) -> RetrievedDocument: ...
def raw_candidates_to_evidence_items(candidates: list[RawCandidate], ...) -> list[CollectedItem]: ...
```

**Naming**: Legacy dataclass `RetrievalResult` in `answer_service.py` SHOULD be renamed
`LegacyRetrievalOutcome` in implementation phase to avoid collision with
`core.retrieval_engine.models.RetrievalResult`.

---

## RetrieverRegistry Wiring

At factory startup:

```text
registry = RetrieverRegistry()
registry.register_retriever(PgVectorDenseRetriever(...))
registry.register_retriever(PgVectorSparseRetriever(...))
registry.register_retriever(StructuredInteractionRetriever(...))
registry.register_defaults(...)  # fuser, expander from engine defaults
pipeline = registry.build_pipeline(RetrievalEngineConfig(...))
```

Config values (`rrf_k`, `candidates`, hybrid flag) sourced from `Settings` + field-pack overrides.

---

## Adapter Test Matrix

| Adapter | Unit test focus | Integration test focus |
|---------|-----------------|------------------------|
| PgVectorDenseRetriever | Mock vectordb client; scoped vs unscoped | Real pgvector query |
| PgVectorSparseRetriever | Hybrid disabled → not called | FTS + vector fusion |
| LegacyRerankerAdapter | Score ordering preserved | End-to-end rerank |
| SqlChunkReader | Missing chunk → None | Load real chunk fixture |
| type_mapping | Round-trip id/score/text | Evidence pack assembly |

---

## Non-Goals (v1)

- Qdrant-specific adapter (follow-up if `VECTOR_DB_BACKEND=qdrant` must support unified path)
- New embedding model integration
- Knowledge graph retriever (spec 008)

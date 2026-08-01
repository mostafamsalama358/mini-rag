from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency', ['method', 'endpoint'])

# ---------------------------------------------------------------------------
# RAG pipeline metrics (retrieval quality + latency observability)
# ---------------------------------------------------------------------------
RAG_RETRIEVAL_COUNT = Counter(
    'rag_retrieval_total',
    'Total RAG retrieval calls',
    ['project_id', 'query_type'],
)
RAG_RETRIEVAL_LATENCY = Histogram(
    'rag_retrieval_latency_seconds',
    'Time spent in the retrieval stage (search + rerank + enrich)',
    ['project_id'],
)
RAG_GENERATION_LATENCY = Histogram(
    'rag_generation_latency_seconds',
    'Time spent generating the final answer',
    ['project_id'],
)
RAG_RERANK_LATENCY = Histogram(
    'rag_rerank_latency_seconds',
    'Time spent in the cross-encoder rerank stage',
    ['project_id', 'backend'],
)
RAG_RERANK_DOCS = Histogram(
    'rag_rerank_docs_count',
    'Number of candidates sent into the cross-encoder reranker',
    ['project_id', 'backend'],
)
RAG_RERANK_STARTUP_LATENCY = Histogram(
    'rag_rerank_startup_latency_seconds',
    'Reranker startup latency (model load and warmup)',
    ['backend', 'stage'],
)
RAG_RETRIEVAL_DOCS = Histogram(
    'rag_retrieved_docs_count',
    'Number of documents returned to the prompt stage',
    ['project_id'],
)
RAG_TOP_SCORE = Histogram(
    'rag_top_score',
    'Top retrieved-document score after fusion (cosine 0..1 domain)',
    ['project_id'],
)
RAG_NO_CONTEXT_TOTAL = Counter(
    'rag_no_context_total',
    'RAG queries that returned no usable context',
    ['project_id'],
)
RAG_CLARIFICATION_TOTAL = Counter(
    'rag_clarification_total',
    'RAG answers flagged as needing clarification',
    ['project_id'],
)
RAG_PARSE_LATENCY = Histogram(
    'rag_parse_latency_seconds',
    'Semantic query parser stage latency',
    ['project_id', 'domain_key', 'outcome'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0),
)

# Document Intelligence stage (spec 006 NFR-007)
DI_PARSE_TOTAL = Counter(
    'document_intelligence_parse_total',
    'Document Intelligence parse outcomes',
    ['source_format', 'outcome'],
)
DI_DEGRADED_TOTAL = Counter(
    'document_intelligence_degraded_total',
    'Document Intelligence degraded extractions by reason',
    ['source_format', 'reason'],
)
DI_ELEMENTS = Histogram(
    'document_intelligence_elements',
    'Structural element counts emitted per parse',
    ['source_format', 'element_type'],
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000),
)

CONTEXT_BUILDER_PIPELINE_DURATION = Histogram(
    'context_builder_pipeline_duration_seconds',
    'Context Builder pipeline stage latency',
    ['stage'],
)
CONTEXT_BUILDER_ITEMS_DROPPED = Counter(
    'context_builder_items_dropped_total',
    'Evidence items dropped during Context Builder assembly',
    ['reason'],
)
CONTEXT_BUILDER_CONFLICTS_DETECTED = Counter(
    'context_builder_conflicts_detected_total',
    'Conflict groups detected by Context Builder',
    ['entity_tag'],
)

ANSWER_GENERATION_DURATION_SECONDS = Histogram(
    'answer_generation_duration_seconds',
    'Answer Generation pipeline stage latency (excluding LLM round-trip is not separated)',
    buckets=(0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)
ANSWER_GENERATION_CITATION_RESOLUTION_TOTAL = Counter(
    'citation_resolution_total',
    'Citations resolved during Answer Generation',
)
ANSWER_GENERATION_NO_ANSWER_TOTAL = Counter(
    'no_answer_total',
    'Answer Generation runs that returned an explicit no-answer result',
)
ANSWER_GENERATION_GROUNDING_FLAG_TOTAL = Counter(
    'grounding_flag_total',
    'Grounding flags emitted during Answer Generation',
)

# Unified production pipeline migration (015)
RAG_PIPELINE_REQUESTS_TOTAL = Counter(
    'rag_pipeline_requests_total',
    'Total RAG pipeline router requests by mode and outcome',
    ['mode', 'outcome'],
)
RAG_PIPELINE_STAGE_DURATION = Histogram(
    'rag_pipeline_stage_duration_seconds',
    'Per-stage wall time inside the unified / routed pipeline',
    ['stage', 'status'],
)
RAG_SHADOW_DIVERGENCE_TOTAL = Counter(
    'rag_shadow_divergence_total',
    'Shadow dual-run comparisons flagged as diverged',
    ['project_id'],
)
PIPELINE_FALLBACK_TOTAL = Counter(
    'pipeline_fallback_total',
    'Unified-path failures that fell back to the legacy executor',
    ['reason'],
)

# Ingest reliability / scalability (017)
INGEST_ADMISSION_TOTAL = Counter(
    'ingest_admission_total',
    'Ingest admission outcomes',
    ['outcome', 'reason'],
)
INGEST_STAGE_DURATION = Histogram(
    'ingest_stage_duration_seconds',
    'Ingest stage wall time',
    ['stage', 'workload_class'],
)
INGEST_PARSE_OUTCOME_TOTAL = Counter(
    'ingest_parse_outcome_total',
    'Ingest parse outcome classifications',
    ['outcome'],
)
INGEST_PROGRESS_EVENTS_TOTAL = Counter(
    'ingest_progress_events_total',
    'Ingest progress kind transitions',
    ['kind'],
)
INGEST_PUBLISH_TOTAL = Counter(
    'ingest_publish_total',
    'Ingest publish completions and exactly-once no-ops',
    ['result'],
)
INGEST_CAPACITY_CLAIM_LEAKS_TOTAL = Counter(
    'ingest_capacity_claim_leaks_total',
    'Detected held capacity claims past terminal without release',
)
INGEST_ORPHAN_RECOVERY_TOTAL = Counter(
    'ingest_orphan_recovery_total',
    'Orphan recovery outcomes',
    ['outcome'],
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Record metrics after request is processed
        duration = time.time() - start_time
        endpoint = request.url.path

        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()

        return response
    
def setup_metrics(app: FastAPI):
    """
    Setup Prometheus metrics middleware and endpoint
    """
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)

    @app.get("/TrhBVe_m5gg2522_esvVqS", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

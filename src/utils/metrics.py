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

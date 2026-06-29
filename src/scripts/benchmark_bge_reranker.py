"""Benchmark local BGE reranker settings on this machine.

Usage (from ``src/``):
    python scripts/benchmark_bge_reranker.py

Reads ``.env`` via ``get_settings()`` and prints the fastest CPU-friendly
``batch_size`` / ``max_chars`` pair for reranking 30 candidates.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from helpers.config import get_settings
from utils.rerank.bge_reranker import BgeReranker


def _sample_passages(count: int, char_length: int) -> list[str]:
    base = (
        "This passage discusses procurement rules, eligibility criteria, and "
        "submission deadlines for public tenders. "
    )
    passage = (base * max(1, char_length // len(base) + 1))[:char_length]
    return [f"{passage} Document {index + 1}." for index in range(count)]


def _benchmark_once(
    *,
    reranker: BgeReranker,
    query: str,
    passages: list[str],
    batch_size: int,
    max_chars: int,
) -> float:
    reranker.batch_size = max(1, batch_size)
    reranker.max_chars = max_chars
    pairs = [[query, reranker._prepare_text(text)] for text in passages]
    started = time.perf_counter()
    reranker.reranker.compute_score(pairs, batch_size=reranker.batch_size, normalize=True)
    return time.perf_counter() - started


def _load_settings():
    try:
        return get_settings()
    except Exception as exc:
        print(f"Warning: could not load .env settings ({exc}); using CLI/defaults.")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark BGE reranker CPU settings.")
    parser.add_argument("--model", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--use-fp16", action="store_true")
    parser.add_argument("--candidates", type=int, default=30, help="Candidate count to rerank.")
    parser.add_argument(
        "--batch-sizes",
        default="4,8,16",
        help="Comma-separated batch sizes to try.",
    )
    parser.add_argument(
        "--max-chars-list",
        default="512,1024,1536",
        help="Comma-separated passage char limits to try.",
    )
    parser.add_argument(
        "--passage-chars",
        type=int,
        default=1200,
        help="Synthetic passage length before max_chars truncation.",
    )
    args = parser.parse_args()

    settings = _load_settings()
    batch_sizes = [int(value.strip()) for value in args.batch_sizes.split(",") if value.strip()]
    max_chars_list = [int(value.strip()) for value in args.max_chars_list.split(",") if value.strip()]
    query = "What are the eligibility criteria and submission deadlines?"

    model_name = args.model
    device = args.device
    use_fp16 = args.use_fp16
    current_batch = 8
    current_max_chars = 1024
    if settings is not None:
        model_name = getattr(settings, "BGE_RERANKER_MODEL", model_name)
        device = getattr(settings, "RAG_RERANKER_DEVICE", device)
        use_fp16 = getattr(settings, "RAG_RERANKER_USE_FP16", use_fp16)
        current_batch = getattr(settings, "RAG_RERANKER_BATCH_SIZE", current_batch)
        current_max_chars = getattr(settings, "RAG_RERANKER_MAX_CHARS", current_max_chars)

    print("Loading BGE reranker for benchmark...")
    reranker = BgeReranker(
        model_name=model_name,
        top_n=5,
        device=device,
        batch_size=current_batch,
        use_fp16=use_fp16,
        max_chars=current_max_chars,
    )
    if not reranker.reranker:
        print("BGE reranker failed to initialize. Install FlagEmbedding and retry.")
        return 1

    print(f"Model load time: {reranker.load_duration_seconds:.2f}s on {reranker.device}")
    passages = _sample_passages(args.candidates, args.passage_chars)

    # Warm up once so timings reflect steady-state inference.
    _benchmark_once(
        reranker=reranker,
        query=query,
        passages=passages[:2],
        batch_size=batch_sizes[0],
        max_chars=max_chars_list[0],
    )

    results: list[tuple[float, int, int]] = []
    print(f"\nBenchmarking {args.candidates} candidates:")
    print(f"{'batch_size':>10} {'max_chars':>10} {'seconds':>10}")
    print("-" * 34)
    for max_chars in max_chars_list:
        for batch_size in batch_sizes:
            elapsed = _benchmark_once(
                reranker=reranker,
                query=query,
                passages=passages,
                batch_size=batch_size,
                max_chars=max_chars,
            )
            results.append((elapsed, batch_size, max_chars))
            print(f"{batch_size:>10} {max_chars:>10} {elapsed:>10.3f}")

    best_elapsed, best_batch, best_max_chars = min(results, key=lambda item: item[0])
    current_elapsed = next(
        (
            elapsed
            for elapsed, batch_size, max_chars in results
            if batch_size == current_batch and max_chars == current_max_chars
        ),
        None,
    )

    print("\nRecommended settings for this machine:")
    print(f"  RAG_RERANKER_BATCH_SIZE={best_batch}")
    print(f"  RAG_RERANKER_MAX_CHARS={best_max_chars}")
    print(f"  Estimated rerank time for {args.candidates} docs: {best_elapsed:.3f}s")

    if current_elapsed is not None:
        print("\nCurrent settings:")
        print(f"  RAG_RERANKER_BATCH_SIZE={current_batch}")
        print(f"  RAG_RERANKER_MAX_CHARS={current_max_chars}")
        print(f"  Estimated rerank time: {current_elapsed:.3f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

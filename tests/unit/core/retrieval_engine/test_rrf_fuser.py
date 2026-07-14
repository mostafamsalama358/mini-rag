"""Unit tests for RRFScoreFuser."""

from __future__ import annotations

from core.retrieval_engine.fusion.rrf import RRFScoreFuser
from core.retrieval_engine.models import RawCandidate


def _c(chunk_id: str, score: float = 1.0) -> RawCandidate:
    return RawCandidate(
        chunk_id=chunk_id,
        document_id="d1",
        raw_score=score,
        retriever_id="r",
        strategy="semantic",
        expander_variant_id="v0",
    )


def test_rrf_overlapping_lists():
    fuser = RRFScoreFuser(k=60)
    a = [_c("x"), _c("y"), _c("z")]
    b = [_c("y"), _c("x"), _c("w")]
    fused = fuser.fuse([a, b])
    ids = [c.chunk_id for c in fused]
    assert len(ids) == len(set(ids))
    # y appears rank1 in b and rank2 in a → highest combined
    assert ids[0] in {"x", "y"}
    score_y = 1 / (60 + 2) + 1 / (60 + 1)
    score_x = 1 / (60 + 1) + 1 / (60 + 2)
    assert abs(score_y - score_x) < 1e-12
    by_id = {c.chunk_id: c.raw_score for c in fused}
    assert abs(by_id["y"] - score_y) < 1e-9
    assert abs(by_id["x"] - score_x) < 1e-9


def test_single_list_unchanged():
    fuser = RRFScoreFuser()
    one = [_c("a"), _c("b")]
    assert [c.chunk_id for c in fuser.fuse([one])] == ["a", "b"]


def test_empty_returns_empty():
    assert RRFScoreFuser().fuse([]) == []


def test_no_duplicate_chunk_ids():
    fuser = RRFScoreFuser()
    fused = fuser.fuse([[_c("a"), _c("b")], [_c("a"), _c("c")]])
    assert len({c.chunk_id for c in fused}) == len(fused)


def test_descending_order():
    fuser = RRFScoreFuser(k=60)
    fused = fuser.fuse([[_c("a"), _c("b")], [_c("a")]])
    scores = [c.raw_score for c in fused]
    assert scores == sorted(scores, reverse=True)

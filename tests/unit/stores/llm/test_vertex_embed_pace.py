import tempfile
import time

from utils.vertex_embed_pace import reserve_vertex_embed_slot


def test_zero_interval_does_not_block():
    started = time.perf_counter()
    reserve_vertex_embed_slot(0, lock_dir=tempfile.mkdtemp())
    assert time.perf_counter() - started < 0.2


def test_second_call_waits_for_the_interval():
    lock_dir = tempfile.mkdtemp()
    reserve_vertex_embed_slot(0.05, lock_dir=lock_dir)
    started = time.perf_counter()
    reserve_vertex_embed_slot(0.05, lock_dir=lock_dir)
    assert time.perf_counter() - started >= 0.04

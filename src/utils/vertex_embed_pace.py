"""Cross-process spacing for Vertex embedding calls.

The project quota is 5 embedding requests per minute. API and Celery workers
are separate processes, so the gap is enforced with a lock file.
"""

from __future__ import annotations

import os
import tempfile
import time

_LOCK_NAME = "algorag_vertex_embed.lock"
_STAMP_NAME = "algorag_vertex_embed.stamp"
_STALE_LOCK_SECONDS = 180.0


def reserve_vertex_embed_slot(
    interval_seconds: float,
    *,
    lock_dir: str | None = None,
) -> None:
    """Block until ``interval_seconds`` have passed since the previous slot."""
    interval = float(interval_seconds or 0)
    if interval <= 0:
        return

    directory = lock_dir or tempfile.gettempdir()
    os.makedirs(directory, exist_ok=True)
    lock_path = os.path.join(directory, _LOCK_NAME)
    stamp_path = os.path.join(directory, _STAMP_NAME)

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            break
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(lock_path)
            except OSError:
                age = 0
            if age > _STALE_LOCK_SECONDS:
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
                continue
            time.sleep(0.25)

    try:
        last = 0.0
        try:
            with open(stamp_path, "r", encoding="utf-8") as handle:
                last = float(handle.read().strip() or 0)
        except (OSError, ValueError):
            last = 0.0
        wait = interval - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        with open(stamp_path, "w", encoding="utf-8") as handle:
            handle.write(str(time.time()))
    finally:
        os.close(fd)
        try:
            os.remove(lock_path)
        except OSError:
            pass

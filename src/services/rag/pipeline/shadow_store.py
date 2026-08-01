"""Shadow comparison JSONL persistence."""

from __future__ import annotations

import json
from pathlib import Path

from services.rag.pipeline.models import ShadowComparisonRecord


class ShadowComparisonStore:
    """Append-only JSONL writer for shadow dual-run diagnostics."""

    def __init__(self, root_dir: str | Path) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, project_id: int) -> Path:
        return self._root / f"project_{project_id}.jsonl"

    async def save(self, record: ShadowComparisonRecord) -> None:
        path = self._path_for(record.project_id)
        line = record.model_dump_json()
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")

    def read_all(self, project_id: int) -> list[dict]:
        path = self._path_for(project_id)
        if not path.exists():
            return []
        rows: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

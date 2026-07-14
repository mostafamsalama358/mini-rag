"""Optional KnowledgeRepresentationStrategy implementations."""

from __future__ import annotations

from typing import Any

from core.knowledge.interfaces import KnowledgeRepresentationStrategy
from core.knowledge.models import KnowledgePackage

__all__ = [
    "KnowledgeRepresentationStrategy",
    "NoOpRepresentationStrategy",
    "StubGraphRepresentationStrategy",
    "StubRelationalRepresentationStrategy",
]


class NoOpRepresentationStrategy:
    """Returns None — useful when representation is not configured."""

    @property
    def strategy_id(self) -> str:
        return "noop"

    def apply(self, package: KnowledgePackage) -> None:
        _ = package
        return None


class StubGraphRepresentationStrategy:
    """Minimal graph projection for tests (nodes + edges)."""

    @property
    def strategy_id(self) -> str:
        return "stub_graph"

    def apply(self, package: KnowledgePackage) -> dict[str, Any]:
        nodes = [
            {"id": u.id, "type": u.type, "content": u.semantic_content}
            for u in package.knowledge_units
        ]
        edges = [
            {
                "id": r.id,
                "type": r.relationship_type,
                "source": r.source_unit_id,
                "target": r.target_unit_id,
            }
            for r in package.knowledge_relationships
        ]
        return {"nodes": nodes, "edges": edges}


class StubRelationalRepresentationStrategy:
    """Minimal relational projection for tests (list of row dicts)."""

    @property
    def strategy_id(self) -> str:
        return "stub_relational"

    def apply(self, package: KnowledgePackage) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for unit in package.knowledge_units:
            rows.append(
                {
                    "kind": "unit",
                    "id": unit.id,
                    "type": unit.type,
                    "text": unit.semantic_content.get("text"),
                }
            )
        for rel in package.knowledge_relationships:
            rows.append(
                {
                    "kind": "relationship",
                    "id": rel.id,
                    "type": rel.relationship_type,
                    "source": rel.source_unit_id,
                    "target": rel.target_unit_id,
                }
            )
        return rows

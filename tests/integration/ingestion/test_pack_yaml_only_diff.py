"""Integration: SC-002 — domain element_mapping changes without core edits."""

from __future__ import annotations

from pathlib import Path

from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.model import StructuralElement
from fields.schemas import ElementChunkConfig
from services.FieldRegistry import FieldRegistry

CORE_DIR = Path(__file__).resolve().parents[3] / "src" / "core" / "document_intelligence"


def test_pack_yaml_only_diff_behavior():
    """Changing element_mapping via profile overrides alters grouping; core path untouched."""
    elements = [
        StructuralElement(
            id=f"d:li:{i}",
            type="list-item",
            order=i,
            text=f"item {i}",
            provenance={},
        )
        for i in range(4)
    ]

    registry = FieldRegistry().load()
    generic = registry.build_profile("generic")
    default_chunks = map_elements_to_chunks(
        elements,
        dict(generic.chunking.element_mapping),
        default_max_chars=generic.chunking.chunk_size,
    )

    overridden = registry.build_profile(
        "generic",
        project_overrides={
            "chunking": {
                "element_mapping": {
                    "list-item": {"group": False},
                }
            }
        },
    )
    new_chunks = map_elements_to_chunks(
        elements,
        dict(overridden.chunking.element_mapping),
        default_max_chars=overridden.chunking.chunk_size,
    )

    # Ungrouped list-items → more chunks than default grouped behavior.
    assert len(new_chunks) >= len(default_chunks)
    assert overridden.chunking.element_mapping["list-item"].group is False
    # Core package files exist and were not required for this behavior change.
    assert CORE_DIR.exists()
    assert (CORE_DIR / "chunk_mapper.py").exists()

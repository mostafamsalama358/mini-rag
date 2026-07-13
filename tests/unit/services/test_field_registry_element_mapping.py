"""Unit: element_mapping merges generic < domain < project (US3)."""

from __future__ import annotations

from services.FieldRegistry import FieldRegistry


def test_element_mapping_precedence():
    registry = FieldRegistry().load()
    generic = registry.build_profile("generic")
    assert "table-row" in generic.chunking.element_mapping
    assert generic.chunking.element_mapping["table-row"].group is False

    pharmacy = registry.build_profile("pharmacy")
    assert pharmacy.chunking.element_mapping["table-row"].group is False

    overridden = registry.build_profile(
        "pharmacy",
        project_overrides={
            "chunking": {
                "element_mapping": {
                    "table-row": {"group": True, "max_chunk_chars": 400},
                }
            }
        },
    )
    assert overridden.chunking.element_mapping["table-row"].group is True
    assert overridden.chunking.element_mapping["table-row"].max_chunk_chars == 400

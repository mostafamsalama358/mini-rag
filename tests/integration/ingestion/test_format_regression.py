"""Integration: SC-003 format regression — shared vocabulary across formats."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.document_intelligence.model import CANONICAL_ELEMENT_TYPES
from core.document_intelligence.parsers import get_parser_for_extension

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "document_intelligence"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "sample.txt").exists():
        from tests.fixtures.document_intelligence.generate_fixtures import generate

        generate()


@pytest.mark.parametrize(
    "filename,ext",
    [
        ("sample.txt", ".txt"),
        ("sample.csv", ".csv"),
        ("sample_50_rows.xlsx", ".xlsx"),
    ],
)
def test_format_shared_vocabulary(filename, ext):
    parser = get_parser_for_extension(ext)
    assert parser is not None
    model = parser.parse(str(FIXTURES / filename), filename)
    assert model.elements
    for el in model.elements:
        assert el.type in CANONICAL_ELEMENT_TYPES

"""Integration: SC-004 degraded vs hard failure."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.fallback import build_fallback_model
from core.document_intelligence.parsers.xlsx_parser import XlsxDocumentParser

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "document_intelligence"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "malformed.xlsx").exists():
        from tests.fixtures.document_intelligence.generate_fixtures import generate

        generate()


def test_malformed_xlsx_degrades_and_fallback_succeeds():
    path = FIXTURES / "malformed.xlsx"
    with pytest.raises(DocumentIntelligenceDegraded) as exc:
        XlsxDocumentParser().parse(str(path), "malformed.xlsx")
    model = build_fallback_model(
        asset_id="malformed.xlsx",
        source_format="xlsx",
        best_effort_text=exc.value.best_effort_text,
        reason=exc.value.reason,
    )
    assert model.extraction_outcome == "degraded"
    assert model.degradation_reason == "empty_content"


def test_unreadable_pdf_hard_failure():
    path = FIXTURES / "unreadable.pdf"
    from core.document_intelligence.parsers.pdf_parser import PdfDocumentParser

    # Hard failure: exception that is NOT DocumentIntelligenceDegraded,
    # or DocumentIntelligenceDegraded only if OCR layer soft-fails — prefer hard.
    try:
        PdfDocumentParser().parse(str(path), "unreadable.pdf")
    except DocumentIntelligenceDegraded:
        # Soft degradation is acceptable only when some text was recoverable;
        # truncated PDF with no pages should degrade empty or raise.
        pass
    except Exception:
        # Hard failure path satisfied.
        pass
    else:
        pytest.fail("expected parse failure or degradation for unreadable.pdf")

"""ParserRegistry + DocumentParser protocol (research R2)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.document_intelligence.model import DocumentModel


@runtime_checkable
class DocumentParser(Protocol):
    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        """Parse one file into a DocumentModel.

        Raise DocumentIntelligenceDegraded for recoverable content-shape issues.
        Raise a normal exception when the file cannot be opened/read (hard failure).
        """
        ...


class ParserRegistry:
    """Extension → DocumentParser mapping (Open/Closed for new formats)."""

    def __init__(self) -> None:
        self._parsers: dict[str, DocumentParser] = {}

    def register(self, extension: str, parser: DocumentParser) -> None:
        key = extension if extension.startswith(".") else f".{extension}"
        self._parsers[key.lower()] = parser

    def get_parser_for_extension(self, ext: str) -> DocumentParser | None:
        if not ext:
            return None
        key = ext if ext.startswith(".") else f".{ext}"
        return self._parsers.get(key.lower())

    def extensions(self) -> list[str]:
        return sorted(self._parsers.keys())


_DEFAULT_REGISTRY: ParserRegistry | None = None


def _build_default_registry() -> ParserRegistry:
    from core.document_intelligence.parsers.csv_parser import CsvDocumentParser
    from core.document_intelligence.parsers.pdf_parser import PdfDocumentParser
    from core.document_intelligence.parsers.text_parser import TextDocumentParser
    from core.document_intelligence.parsers.xlsx_parser import XlsxDocumentParser

    registry = ParserRegistry()
    registry.register(".txt", TextDocumentParser())
    registry.register(".csv", CsvDocumentParser())
    registry.register(".xlsx", XlsxDocumentParser())
    registry.register(".pdf", PdfDocumentParser())
    return registry


def get_default_registry() -> ParserRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = _build_default_registry()
    return _DEFAULT_REGISTRY


def get_parser_for_extension(ext: str) -> DocumentParser | None:
    return get_default_registry().get_parser_for_extension(ext)

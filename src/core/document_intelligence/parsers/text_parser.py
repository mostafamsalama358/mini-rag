"""Plain text → paragraph StructuralElements."""

from __future__ import annotations

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import DocumentModel, StructuralElement, make_element_id


class TextDocumentParser:
    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        fingerprint = file_id
        try:
            with open(file_path, encoding="utf-8") as handle:
                raw = handle.read()
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            raise DocumentIntelligenceDegraded("parse_error", str(exc)) from exc

        text = (raw or "").strip()
        if not text:
            raise DocumentIntelligenceDegraded("empty_content", "empty text file")

        # Prefer structural boundaries when available; otherwise split on blank lines.
        try:
            from core.structural.engine import split_at_structural_boundaries

            segments = split_at_structural_boundaries(text)
        except Exception:
            segments = [p.strip() for p in text.split("\n\n") if p.strip()] or [text]

        elements: list[StructuralElement] = []
        for order, segment in enumerate(segments):
            elements.append(
                StructuralElement(
                    id=make_element_id(fingerprint, f"para:{order}"),
                    type="paragraph",
                    order=order,
                    text=segment,
                    provenance={"file_name": file_id},
                )
            )

        return DocumentModel(
            asset_id=file_id,
            source_format="txt",
            elements=elements,
            extraction_outcome="full",
        )

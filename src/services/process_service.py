"""
services/process_service.py — File Processing Service
.NET Equivalent: IFileProcessingService

This service is responsible for reading files from disk, running OCR if needed,
and splitting the text into smaller chunks for vector database indexing.

Moved here from `controllers/ProcessController.py` as part of the 003 refactor.
Spec 006: Document Intelligence (ParserRegistry → DocumentModel → chunk_mapper).
"""
from .base import BaseController
from .project_service import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models import ProcessingEnum
from typing import List
from dataclasses import dataclass
from utils.text_cleaning import clean_extracted_text
from utils.chunk_metadata import normalize_chunk_metadata
from utils.chunk_sizing import resolve_chunk_params
from core.structural.engine import split_at_structural_boundaries
from services.FieldRegistry import FieldProfile
from helpers.config import get_settings

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.fallback import build_fallback_model
from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.model import DocumentModel
from core.document_intelligence.parsers import get_parser_for_extension
from core.field_resolution import build_field_manifest


@dataclass
class Document:
    page_content: str
    metadata: dict


class DocumentBatch(list):
    """List of Documents that can carry sidecar attrs (manifest, model, extraction).

    Plain ``list`` rejects ``setattr`` on CPython 3.11+, which breaks field-manifest
    and DocumentModel propagation from loaders into the Celery task.
    """

    def __init__(self, iterable=()) -> None:
        super().__init__(iterable)
        self.document_model: DocumentModel | None = None
        self.field_manifest: object | None = None
        self.extraction: dict | None = None


class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]

    def get_file_loader(self, file_id: str):

        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(
            self.project_path,
            file_id
        )

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        return None

    def _parse_document_model(self, file_path: str, file_id: str, file_ext: str) -> DocumentModel | None:
        """Parse via Document Intelligence registry; degrade on soft failures."""
        parser = get_parser_for_extension(file_ext)
        if parser is None:
            return None
        source_format = file_ext.lstrip(".") or "unknown"
        try:
            model = parser.parse(file_path, file_id)
            self._record_di_metrics(model)
            return model
        except DocumentIntelligenceDegraded as exc:
            model = build_fallback_model(
                asset_id=file_id,
                source_format=source_format,
                best_effort_text=exc.best_effort_text,
                reason=exc.reason,
                asset_fingerprint=file_id,
            )
            self._record_di_metrics(model)
            return model
        except (FileNotFoundError, OSError):
            raise
        except Exception:
            # Hard open/read failure → caller treats None as ingestion error.
            return None

    @staticmethod
    def _record_di_metrics(model: DocumentModel) -> None:
        try:
            from utils.metrics import DI_DEGRADED_TOTAL, DI_ELEMENTS, DI_PARSE_TOTAL

            fmt = model.source_format or "unknown"
            DI_PARSE_TOTAL.labels(source_format=fmt, outcome=model.extraction_outcome).inc()
            if model.extraction_outcome == "degraded" and model.degradation_reason:
                DI_DEGRADED_TOTAL.labels(
                    source_format=fmt,
                    reason=model.degradation_reason,
                ).inc()
            for element_type, count in model.element_counts().items():
                DI_ELEMENTS.labels(source_format=fmt, element_type=element_type).observe(count)
        except Exception:
            pass
    def _documents_from_model(self, model: DocumentModel, file_id: str) -> DocumentBatch:
        """Render a DocumentModel as langchain-compatible Documents (compat shim)."""
        from langchain.schema import Document as LCDocument

        docs = DocumentBatch()
        for el in model.elements:
            if el.type == "table-row" and el.fields is not None:
                line = ", ".join(f"{k}: {v}" for k, v in el.fields.items())
                sheet = (el.provenance or {}).get("sheet_name", "")
                text = f"[{file_id} | {sheet}] {line}" if sheet else line
                meta = {
                    **dict(el.provenance or {}),
                    "fields": dict(el.fields),
                    **{f"col_{k}": v for k, v in el.fields.items()},
                    "element_type": el.type,
                    "source_element_ids": [el.id],
                    "file_name": file_id,
                }
            else:
                text = el.text or ""
                meta = {
                    **dict(el.provenance or {}),
                    "element_type": el.type,
                    "source_element_ids": [el.id],
                    "file_name": file_id,
                }
            docs.append(LCDocument(page_content=text, metadata=meta))

        docs.document_model = model
        if model.elements and any(el.type == "table-row" for el in model.elements):
            row_metas = [
                {
                    **dict(el.provenance or {}),
                    "fields": dict(el.fields or {}),
                }
                for el in model.elements
                if el.type == "table-row"
            ]
            manifest = build_field_manifest(row_metas) if row_metas else None
            if manifest is not None:
                docs.field_manifest = manifest
        return docs

    def get_file_content(self, file_id: str, *, strategy: str | None = None):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        # Spec 006: prefer Document Intelligence ParserRegistry for supported formats.
        model = self._parse_document_model(file_path, file_id, file_ext)
        if model is not None:
            return self._documents_from_model(model, file_id)

        # Legacy loaders for anything not yet registered.
        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8").load()

        if file_ext == ProcessingEnum.PDF.value:
            from utils.pdf_ocr import load_pdf_with_ocr_fallback
            return load_pdf_with_ocr_fallback(file_path)

        if file_ext == ProcessingEnum.CSV.value:
            from langchain_community.document_loaders.csv_loader import CSVLoader
            return CSVLoader(file_path=file_path, encoding="utf-8").load()

        if file_ext == ProcessingEnum.XLSX.value:
            return self._load_xlsx(file_path, file_id, row_chunking=(strategy == "row"))

        return None

    def _load_xlsx(self, file_path: str, file_id: str, *, row_chunking: bool = False):
        """Load an .xlsx file (legacy path / compat)."""
        from langchain.schema import Document as LCDocument
        from core.chunking.engine import row_chunk_xlsx

        if row_chunking:
            try:
                records = row_chunk_xlsx(file_path, file_id)
            except Exception:
                return None
            if not records:
                return DocumentBatch([LCDocument(page_content="Empty Excel File")])
            docs = DocumentBatch(
                LCDocument(page_content=rec["text"], metadata=rec["metadata"])
                for rec in records
            )
            manifest = getattr(records, "field_manifest", None)
            if manifest is not None:
                docs.field_manifest = manifest
            return docs

        import pandas as pd
        try:
            dfs = pd.read_excel(file_path, sheet_name=None)
        except Exception:
            return None
        text_content = ""
        for sheet_name, df in dfs.items():
            if df.empty:
                continue
            text_content += f"--- Sheet: {sheet_name} ---\n"
            text_content += df.to_csv(index=False)
            text_content += "\n\n"
        if not text_content.strip():
            text_content = "Empty Excel File"
        return [LCDocument(page_content=text_content)]

    def _normalize_loader_metadata(self, metadata: dict, file_id: str, source_type: str) -> dict:
        normalized = normalize_chunk_metadata(metadata or {})
        page = normalized.get("page")
        if page is not None:
            try:
                normalized["page"] = int(page)
            except (TypeError, ValueError):
                normalized.pop("page", None)

        normalized["file_name"] = normalized.get("file_name") or file_id
        normalized["source_type"] = normalized.get("source_type") or source_type
        normalized.pop("source", None)
        return normalized

    def _split_text(self, text: str, metadata: dict, chunk_size: int, overlap_size: int, *, page_bound: bool = False):
        effective_overlap = 0 if page_bound else overlap_size

        if len(text) <= chunk_size:
            return [Document(page_content=text, metadata=dict(metadata))]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=effective_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        return splitter.create_documents([text], metadatas=[metadata])

    def process_file_content(
        self,
        file_content: list,
        file_id: str,
        chunk_size: int=100,
        overlap_size: int=20,
        *,
        profile: FieldProfile | None = None,
    ):
        """Split loaded file content into chunks.

        When a DocumentModel is attached (spec 006), chunking is driven by
        ``element_mapping`` via ``map_elements_to_chunks``. Otherwise the
        legacy strategy path is used.
        """
        source_type = self.get_file_extension(file_id=file_id).lstrip(".") or "unknown"
        strategy = profile.chunking_strategy_for(source_type) if profile is not None else None

        model: DocumentModel | None = getattr(file_content, "document_model", None)
        if model is not None:
            element_mapping = {}
            default_max = chunk_size
            overlap = overlap_size
            strategy_name = "semantic_structural"
            policy_name = "rule_based"
            if profile is not None:
                element_mapping = dict(profile.chunking.element_mapping or {})
                default_max = int(profile.chunking.chunk_size or chunk_size)
                overlap = int(profile.chunking.overlap or overlap_size)
                strategy_name = str(profile.chunking.strategy or strategy_name)
                policy_name = str(profile.chunking.policy or policy_name)

            from core.chunking.models import ChunkingStrategyConfig
            from core.chunking.registry import get_chunking_strategy

            chunk_config = ChunkingStrategyConfig(
                strategy=strategy_name,
                max_chars=default_max,
                overlap=overlap,
                policy=policy_name,
                element_mapping=element_mapping,
            )
            strategy_impl = get_chunking_strategy(strategy_name, chunk_config)
            chunk_set = strategy_impl.chunk(model, chunk_config)
            records = [{"text": c.text, "metadata": c.metadata} for c in chunk_set.chunks]
            all_chunks = DocumentBatch()
            for rec in records:
                text = clean_extracted_text(rec["text"])
                if not text:
                    continue
                metadata = self._normalize_loader_metadata(
                    rec.get("metadata") or {},
                    file_id=file_id,
                    source_type=source_type,
                )
                all_chunks.append(Document(page_content=text, metadata=metadata))

            all_chunks.document_model = model
            all_chunks.extraction = {
                "outcome": model.extraction_outcome,
                "reason": model.degradation_reason,
                "element_counts": model.element_counts(),
            }
            all_chunks.chunk_set = chunk_set
            manifest = getattr(file_content, "field_manifest", None)
            if manifest is not None:
                all_chunks.field_manifest = manifest
            return all_chunks

        all_chunks = DocumentBatch()

        for rec in file_content:
            text = clean_extracted_text(rec.page_content)
            if not text:
                continue

            metadata = self._normalize_loader_metadata(
                rec.metadata,
                file_id=file_id,
                source_type=source_type,
            )
            for key in ("row_index", "sheet_name", "brand_name"):
                if rec.metadata and rec.metadata.get(key) is not None:
                    metadata[key] = rec.metadata[key]

            page_bound = (
                strategy == "page"
                or (metadata.get("source_type") == "pdf" and metadata.get("page") is not None)
            )

            settings = get_settings()
            effective_chunk_size, effective_overlap = resolve_chunk_params(
                len(text),
                chunk_size,
                overlap_size,
                min_chunk_size=settings.TEXT_CHUNK_MIN_SIZE,
                max_chunk_size=settings.TEXT_CHUNK_MAX_SIZE,
            )

            if strategy == "row" and metadata.get("row_index") is not None:
                all_chunks.append(Document(page_content=text, metadata=dict(metadata)))
                continue

            segments = split_at_structural_boundaries(
                text,
                patterns=profile.structural_patterns if profile is not None else None,
            )
            for segment in segments:
                all_chunks.extend(
                    self._split_text(
                        segment,
                        metadata,
                        effective_chunk_size,
                        effective_overlap,
                        page_bound=page_bound,
                    )
                )

        manifest = getattr(file_content, "field_manifest", None)
        if manifest is not None:
            all_chunks.field_manifest = manifest
        return all_chunks

    def process_simpler_splitter(self, texts: List[str], metadatas: List[dict], chunk_size: int, splitter_tag: str="\n"):

        full_text = " ".join(texts)

        lines = [ doc.strip() for doc in full_text.split(splitter_tag) if len(doc.strip()) > 1 ]

        chunks = []
        current_chunk = ""

        for line in lines:
            current_chunk += line + splitter_tag
            if len(current_chunk) >= chunk_size:
                chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={}
                ))

                current_chunk = ""

        if len(current_chunk) >= 0:
            chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata={}
            ))

        return chunks

    def load_xlsx_rows(self, file_id: str, *, row_chunking: bool = True):
        """Public helper for callers that pre-resolved row chunking."""
        file_path = os.path.join(self.project_path, file_id)
        if not os.path.exists(file_path):
            return None
        return self._load_xlsx(file_path, file_id, row_chunking=row_chunking)

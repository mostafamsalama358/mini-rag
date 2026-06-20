from .BaseController import BaseController
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from models import ProcessingEnum
from typing import List
from dataclasses import dataclass
from utils.text_cleaning import clean_extracted_text
from utils.chunk_metadata import normalize_chunk_metadata
from utils.chunk_sizing import resolve_chunk_params
from utils.structural_split import split_at_structural_boundaries
from helpers.config import get_settings

@dataclass
class Document:
    page_content: str
    metadata: dict

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

    def get_file_content(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8").load()

        if file_ext == ProcessingEnum.PDF.value:
            from utils.pdf_ocr import load_pdf_with_ocr_fallback
            return load_pdf_with_ocr_fallback(file_path)

        return None

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

    def process_file_content(self, file_content: list, file_id: str,
                            chunk_size: int=100, overlap_size: int=20):

        source_type = self.get_file_extension(file_id=file_id).lstrip(".") or "unknown"
        all_chunks = []

        for rec in file_content:
            text = clean_extracted_text(rec.page_content)
            if not text:
                continue

            metadata = self._normalize_loader_metadata(
                rec.metadata,
                file_id=file_id,
                source_type=source_type,
            )
            page_bound = metadata.get("source_type") == "pdf" and metadata.get("page") is not None

            settings = get_settings()
            effective_chunk_size, effective_overlap = resolve_chunk_params(
                len(text),
                chunk_size,
                overlap_size,
                min_chunk_size=settings.TEXT_CHUNK_MIN_SIZE,
                max_chunk_size=settings.TEXT_CHUNK_MAX_SIZE,
            )

            segments = split_at_structural_boundaries(text)
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

        return all_chunks

    def process_simpler_splitter(self, texts: List[str], metadatas: List[dict], chunk_size: int, splitter_tag: str="\n"):
        
        full_text = " ".join(texts)

        # split by splitter_tag
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


    


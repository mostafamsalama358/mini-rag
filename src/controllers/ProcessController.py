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

    def process_file_content(self, file_content: list, file_id: str,
                            chunk_size: int=100, overlap_size: int=20):

        source_type = self.get_file_extension(file_id=file_id).lstrip(".") or "unknown"

        file_content_texts = [
            clean_extracted_text(rec.page_content)
            for rec in file_content
        ]

        file_content_metadata = [
            self._normalize_loader_metadata(rec.metadata, file_id=file_id, source_type=source_type)
            for rec in file_content
        ]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadata,
        )

        return chunks

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


    


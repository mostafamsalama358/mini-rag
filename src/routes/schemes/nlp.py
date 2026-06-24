from pydantic import BaseModel
from typing import Optional

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    # Optional metadata pre-filter applied before retrieval.
    # Supported keys: project_id, asset_id, document_type, category, etc.
    # Example: {"asset_id": 5, "document_type": "pdf"}
    metadata_filter: Optional[dict] = None

class AnswerRequest(BaseModel):
    text: str
    limit: Optional[int] = 8
    session_id: Optional[str] = None
    # Optional metadata pre-filter applied before retrieval.
    # Supported keys: project_id, asset_id, document_type, category, etc.
    metadata_filter: Optional[dict] = None

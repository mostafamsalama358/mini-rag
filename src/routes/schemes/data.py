from pydantic import BaseModel
from typing import Optional

class ProcessRequest(BaseModel):
    file_id: Optional[str] = None
    chunk_size: Optional[int] = None
    overlap_size: Optional[int] = None
    do_reset: Optional[int] = 0

class SuggestMetadataRequest(BaseModel):
    file_names: list[str]

class UpdateMetadataRequest(BaseModel):
    file_names: list[str]
    tags: list[str]

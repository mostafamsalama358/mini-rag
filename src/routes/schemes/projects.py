from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class ProjectPromptUpdateRequest(BaseModel):
    prompt_en: str | None = None
    prompt_ar: str | None = None


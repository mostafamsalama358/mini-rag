from pydantic import BaseModel, Field
from typing import Any


class ProjectPatchRequest(BaseModel):
    # PATCH /projects/{uuid} — update config_json in DB only. [Obsolete]
    config_json: dict[str, Any] | None = None


class ProjectPromptUpdateRequest(BaseModel):
    # PUT /projects/{uuid}/prompt — set prompt overrides. [Obsolete]
    prompt_en: str | None = None
    prompt_ar: str | None = None

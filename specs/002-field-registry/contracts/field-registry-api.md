# Contract: Field Registry API

**Version**: 1.1.0 | **Feature**: `002-field-registry` | **Revised**: domain on `projects` table

## Internal: FieldRegistry

```python
class FieldRegistry:
    def list_fields(self) -> list[FieldSummary]: ...
    def get_pack(self, domain_key: DomainKeyEnum) -> FieldPack: ...
    def build_profile(
        self,
        project: Project,
        *,
        language: str = "en",
    ) -> FieldProfile: ...
```

`build_profile` reads `project.domain_key`, `project.config_json`, `project.prompt_override`.

---

## HTTP: Project includes domain (extend existing project APIs)

No separate `/domain` resource required in v1. Domain is part of **project create/update/get**.

### `GET /api/v1/projects/{project_uuid}` (extended response fields)

```json
{
  "id": "uuid",
  "project_id": 1,
  "name": "Pharmacy Demo",
  "domain_key": "pharmacy",
  "config_json": {},
  "available_domains": [
    { "key": "generic", "label": "Generic RAG" },
    { "key": "pharmacy", "label": "Pharmacy" },
    { "key": "legal", "label": "Legal" }
  ]
}
```

`available_domains` from `FieldRegistry.list_fields()` — optional on list endpoint, included on get/create.

### `POST /api/v1/projects` / `PATCH /api/v1/projects/{project_uuid}`

**Request** (optional fields):

```json
{
  "name": "Pharmacy Demo",
  "domain_key": "pharmacy",
  "config_json": {
    "retrieval": { "exhaustive_min_limit": 60 }
  }
}
```

**Validation**:

| Rule | Behavior |
|------|----------|
| `domain_key` not in enum | `400` invalid domain |
| `config_json` invalid shape | `400` with schema error |
| omit `domain_key` on create | default `generic` |

### Prompts — separate existing API / `project_prompts`

Prompt text stays on `project_prompts` (create/update via existing or dedicated prompt endpoint). **Not** stored in `config_json`.

---

## Pipeline integration

```python
profile = field_registry.build_profile(project, language=detected_lang)
# uses project.domain_key, project.config_json, project.prompt_override
```

Chunking at ingest time:

```python
strategy = profile.chunking.for_extension(file_ext)  # .xlsx → row, .pdf → page
```

---

## Field pack files (per domain directory)

| File | Required |
|------|----------|
| `domain.yaml` | yes |
| `chunking.yaml` | yes (`by_extension`) |
| `retrieval.yaml` | yes |
| `chunk_metadata.yaml` | yes |
| `structural_split.yaml` | no (legal) |
| `prompts/system_{lang}.txt` | no (defaults; override in `project_prompts`) |

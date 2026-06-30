# Data Model: Field Registry

**Feature**: `002-field-registry` | **Date**: 2026-06-29 | **Revised**: 2026-06-29

## Persistent entities (changed)

### `projects` table — extended (no separate domain table)

`domain_key` and `config_json` live **directly on `projects`**. No `project_domain_config` table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `domain_key` | enum / varchar | NOT NULL, default `generic` | Field pack key |
| `config_json` | jsonb | NOT NULL, default `{}` | **Snapshot** of field `project.defaults.yaml` at project creation (+ optional user overrides merged in) |

**Config file → DB on create (mandatory flow)**:

```text
fields/pharmacy/project.defaults.yaml   ──read on POST /projects──►  projects.config_json
fields/legal/project.defaults.yaml
fields/generic/project.defaults.yaml
```

At runtime the pipeline reads **`projects.config_json` only** — not the YAML file directly. The file is the **template**; the DB row is the **project's copy**.

**Python enum** (`models/enums/DomainKeyEnum.py`):

```python
class DomainKeyEnum(str, Enum):
    GENERIC = "generic"
    PHARMACY = "pharmacy"
    LEGAL = "legal"
    # new domains: add here + registry.yaml + Alembic enum migration
```

**DB**: PostgreSQL native `ENUM` or `VARCHAR(32)` with check constraint — prefer `ENUM` for strict values.

**Alembic migration**:

```sql
CREATE TYPE domain_key AS ENUM ('generic', 'pharmacy', 'legal');
ALTER TABLE projects
  ADD COLUMN domain_key domain_key NOT NULL DEFAULT 'generic',
  ADD COLUMN config_json JSONB NOT NULL DEFAULT '{}';
CREATE INDEX ix_projects_domain_key ON projects (domain_key);
```

Existing projects backfill: `domain_key = 'generic'`, `config_json = '{}'`.

**Example `fields/pharmacy/project.defaults.yaml`** (source file in git):

```yaml
version: 1
chunking:
  by_extension:
    .xlsx: row
    .csv: row
    .pdf: page
    .txt: character
  chunk_size: 800
  overlap: 120
retrieval:
  exhaustive_min_limit: 50
  disable_chunk_focus: true
```

**Same content stored in `projects.config_json`** after create (JSON equivalent):

```json
{
  "version": 1,
  "chunking": {
    "by_extension": { ".xlsx": "row", ".csv": "row", ".pdf": "page", ".txt": "character" },
    "chunk_size": 800,
    "overlap": 120
  },
  "retrieval": {
    "exhaustive_min_limit": 50,
    "disable_chunk_focus": true
  }
}
```

User may pass optional `config_json` in create request — **deep-merged on top** of file defaults before save.

`file_roles` deferred to v2 — not required in v1.

---

### `project_prompts` — unchanged

| Column | Purpose |
|--------|---------|
| `prompt_en` | Long English system prompt override |
| `prompt_ar` | Long Arabic system prompt override |

**Separation of concerns**:

| Column / table | Stores |
|----------------|--------|
| `projects.domain_key` | Which template file to load on create |
| `projects.config_json` | Snapshot from `project.defaults.yaml` (+ merges); **runtime source of truth** |
| `project_prompts` | Long prompt text (optional; may also seed from `fields/*/prompts/` on create) |
| `fields/*/retrieval.yaml` etc. | Pack modules used by engine + merged into defaults file |

---

## Project creation flow

```text
POST /projects { name, domain_key: "pharmacy", config_json?: {} }
        │
        ▼
FieldRegistry.load_defaults("pharmacy")
        │  reads fields/pharmacy/project.defaults.yaml
        ▼
merge(file_defaults, request.config_json)
        │
        ▼
INSERT projects (domain_key, config_json, ...)
        │
        ▼
optional: copy prompts from fields/pharmacy/prompts/ → project_prompts
```

**Later edits**: `PATCH /projects/{uuid}` updates `config_json` in DB only — does not rewrite the YAML file.

**New deploy** with updated `project.defaults.yaml` does **not** change existing projects (snapshot model). Optional future: `POST /projects/{uuid}/sync-config` to re-import from file.

## Runtime entities (not persisted)

### FieldPack

Loaded from `src/fields/{domain_key}/`.

| Attribute | Type | Source file |
|-----------|------|-------------|
| `key` | str | directory name |
| `label` | str | `domain.yaml` |
| `languages` | list[str] | `domain.yaml` |
| `chunking` | ChunkingProfile | `chunking.yaml` |
| `retrieval` | RetrievalProfile | `retrieval.yaml` |
| `structural_split` | StructuralProfile | `structural_split.yaml` (optional) |
| `chunk_metadata` | MetadataProfile | `chunk_metadata.yaml` |
| `prompts` | PromptBundle | `prompts/system_{lang}.txt` |

### FieldProfile

Merged at request time:

```text
effective = merge(
  fields.generic.*,
  fields[project.domain_key].*,
  project.config_json,
  project_prompts (prompt text only)
)
```

---

## Profile schemas (YAML → Pydantic)

### ChunkingProfile — **by file extension** (not one strategy per domain)

| Field | Type | Description |
|-------|------|-------------|
| `by_extension` | dict[str, str] | `.xlsx` → `row`, `.pdf` → `page`, `.txt` → `character` |
| `chunk_size` | int | default 800 |
| `overlap` | int | default 120 |

```yaml
# fields/pharmacy/chunking.yaml
by_extension:
  .xlsx: row
  .csv: row
  .pdf: page
  .txt: character
chunk_size: 800
overlap: 120
```

Chunking strategy is chosen from **uploaded file extension** + field defaults — not a single `strategy` for the whole domain.

### RetrievalProfile

| Field | Type | Description |
|-------|------|-------------|
| `intents` | dict[str, IntentRule] | Regex patterns (ar/en) |
| `exhaustive_min_limit` | int | Floor for candidate count |
| `disable_chunk_focus` | bool | For exhaustive queries |

### Other profiles

Unchanged: `StructuralProfile`, `MetadataProfile`, `IntentRule` — see previous revision.

---

## Registry file (`src/fields/registry.yaml`)

```yaml
version: 1
default: generic
fields:
  - key: generic
    label: Generic RAG
  - key: pharmacy
    label: Pharmacy
  - key: legal
    label: Legal
```

Enum in code MUST be subset of registry keys (or registry is source of truth at startup validation).

---

## Entity diagram

```text
fields/registry.yaml
       │
       ▼
  FieldPack (pharmacy, legal, generic)
       │
       │ merge(project.config_json from DB snapshot)
       ▼
  FieldProfile ──► core pipeline
       ▲
       │
Project
  ├── domain_key      (enum on projects)
  ├── config_json     (jsonb on projects)
  └── prompt_override → project_prompts (1:1, optional)
```

---

## Validation rules

1. `projects.domain_key` MUST exist in `registry.yaml` or API rejects on write; on read fall back to `generic`
2. `config_json` MUST NOT exceed 32 KB
3. Adding a new domain: update `DomainKeyEnum` + Alembic enum migration + `registry.yaml` + `fields/{name}/`
4. Changing `domain_key` after indexing SHOULD show re-index warning (app-level)

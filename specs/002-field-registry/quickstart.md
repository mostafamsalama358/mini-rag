# Quickstart: Field Registry Validation

**Feature**: `002-field-registry` | **Revised**: domain on `projects`

## Prerequisites

- Migration applied: `projects.domain_key`, `projects.config_json`
- Field packs under `src/fields/`

## Step 1 — Create pharmacy project

```powershell
curl -X POST "http://localhost:8000/api/v1/projects" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo-user" `
  -d '{"name": "Pharmacy Demo", "domain_key": "pharmacy", "config_json": {}}'
```

**Expected**: Project row has `domain_key = pharmacy`.

## Step 2 — Set pharmacist prompt (existing table)

Store long prompt in `project_prompts` — not in `config_json`.

## Step 3 — Verify chunking by file type

Upload `.xlsx` and `.pdf` to same pharmacy project; process both.

**Expected**:

- `.xlsx` → `chunking_strategy: row` (from `by_extension`)
- `.pdf` → page/structural chunks

## Step 4 — Override via config_json (optional)

```json
PATCH project: { "config_json": { "retrieval": { "exhaustive_min_limit": 60 } } }
```

## Pass criteria

- [ ] `domain_key` enum on `projects` only — no extra domain table
- [ ] `project_prompts` still holds prompt text
- [ ] Chunking follows file extension, not domain alone

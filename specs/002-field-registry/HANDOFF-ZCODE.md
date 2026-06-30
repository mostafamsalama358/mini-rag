# Implementation Handoff — Field Registry + Pharmacy (for Zcode)

**Repo**: `D:/mini-rag` (AlgoRAG / mini-rag)  
**Branch**: `002-field-registry`  
**Do NOT implement**: `specs/001-pharmacy-query-enhancement` (superseded)

## Mission

Implement **one shared RAG engine** + **pluggable field packs** under `src/fields/`. First real pack: **pharmacy**. Fix production pharmacy failures: incomplete drug lists, missing interactions, weak prescription cross-check, follow-up context loss.

Read fully before coding:

- `specs/002-field-registry/spec.md`
- `specs/002-field-registry/plan.md`
- `specs/002-field-registry/data-model.md`
- `specs/002-field-registry/research.md`
- `specs/002-field-registry/contracts/field-registry-api.md`
- `specs/002-field-registry/quickstart.md`
- `.specify/memory/constitution.md`
- `src/ARCHITECTURE.md`

## Core design decisions (non-negotiable)

1. **`src/fields/{domain}/`** — domain configs (YAML + prompt text). NOT scattered `utils/pharmacy/`.
2. **`src/core/`** — shared pipeline (RRF, hybrid, dedupe, chunking engine). NO domain regex here.
3. **`projects.domain_key`** — ENUM on `projects` table (`generic`, `pharmacy`, `legal`).
4. **`projects.config_json`** — JSONB snapshot copied from `fields/{domain}/project.defaults.yaml` **on project create**. Runtime reads DB only, not YAML per request.
5. **`project_prompts`** — long bilingual prompts (existing table). Seed from `fields/pharmacy/prompts/` on create if empty.
6. **Chunking by file extension** — `.xlsx` → `row`, `.pdf` → `page`, NOT one strategy per domain.
7. **No `project_domain_config` table** — columns on `projects` only.
8. **`file_roles` / `catalog`** — deferred v2; skip unless trivial.

## Implementation phases (in order)

### Phase A — Foundation

- [ ] Alembic: add `domain_key` enum + `config_json` jsonb to `projects`; backfill `generic` / `{}`
- [ ] `models/enums/DomainKeyEnum.py`
- [ ] Extend `Project` SQLAlchemy model + Pydantic `ProjectConfig` validator
- [ ] `src/fields/registry.yaml` + packs: `generic/`, `legal/` (stub), `pharmacy/` (stub)
- [ ] Each pack: `domain.yaml`, `project.defaults.yaml`, `chunking.yaml`, `retrieval.yaml`, `chunk_metadata.yaml`
- [ ] `services/FieldRegistry.py`: load packs, validate YAML, `load_project_defaults(domain_key)`, `build_profile_from_db(project)`
- [ ] Wire `FieldRegistry` in `main.py` startup
- [ ] `tests/unit/fields/test_registry.py`, `test_merge.py`

### Phase B — Refactor legal/generic out of utils

- [ ] Create `src/core/retrieval/engine.py` — move `hybrid_rrf`, `deduplicate_retrieved_documents`, `merge_retrieved_documents`, `rerank_retrieved_documents` from `utils/retrieval.py`
- [ ] Create `src/core/structural/engine.py` — patterns from profile, not hard-coded
- [ ] Move legal patterns from `utils/structural_split.py` → `fields/legal/structural_split.yaml` + `fields/legal/retrieval.yaml`
- [ ] `utils/retrieval.py` + `utils/structural_split.py` → thin shims re-exporting core (backward compat)
- [ ] Regression tests with `domain_key=generic` must pass

### Phase C — Pipeline uses FieldProfile

- [ ] `NLPController.search_vector_db_collection` accepts `FieldProfile` (from `project.config_json` + pack modules)
- [ ] `ProcessController.process_file_content` uses `profile.chunking.for_extension(file_ext)`
- [ ] `RAGService.answer_question` uses profile for query classification + `disable_chunk_focus`
- [ ] Extend `POST /api/v1/projects`: `domain_key`, optional `config_json` → read `project.defaults.yaml`, merge, save to DB
- [ ] Extend `serialize_project` to return `domain_key`, `config_json`
- [ ] On create: optional seed `project_prompts` from `fields/{domain}/prompts/`
- [ ] `PATCH /api/v1/projects/{uuid}` for `config_json` updates (optional v1)

### Phase D — Pharmacy pack (merged from archived 001)

- [ ] `fields/pharmacy/project.defaults.yaml` — exhaustive limits, row chunking, disable_chunk_focus
- [ ] `fields/pharmacy/retrieval.yaml` — intents: `exhaustive_list`, `interaction_lookup`, `prescription_check`, `drug_detail`, `comparison`; Arabic/English patterns (`كل الادوية`, `عايزهم كلهم`, `متعارض`, `روشتة`, …)
- [ ] Row chunking for XLSX in `ProcessController` when strategy `row`
- [ ] `core/query_understanding.py` + `fields/pharmacy/query_rewrite.yaml` — LLM rewrite (3s timeout, fallback to rules); use existing `generation_client`
- [ ] Prescription parser (rule-based line split) for multi-drug input
- [ ] Follow-up: inject last drug entity from chat history into rewrite
- [ ] Exhaustive mode: higher limits from `config_json`, `max_output_tokens` 8192, completeness footer
- [ ] Pharmacist prompts in `fields/pharmacy/prompts/system_ar.txt` + `system_en.txt` (user template from conversation)
- [ ] Integration tests: muscle relaxants list, Cordarone interactions, 5-drug prescription
- [ ] Metrics: `domain_key`, query intent, rewrite latency

## Key files to modify

| File | Change |
|------|--------|
| `src/models/db_schemes/algorag/schemes/project.py` | +domain_key, +config_json |
| `src/models/ProjectModel.py` | create with defaults load |
| `src/routes/projects.py` | domain_key on create |
| `src/routes/schemes/projects.py` | Pydantic schemas |
| `src/controllers/ProcessController.py` | row chunking, profile-aware |
| `src/controllers/NLPController.py` | profile + query understanding |
| `src/services/RAGService.py` | profile, exhaustive generation |
| `src/utils/retrieval.py` | shrink to shim |
| `src/utils/structural_split.py` | shrink to shim |

## Project create flow (must implement exactly)

```python
defaults = field_registry.load_project_defaults(domain_key)  # reads YAML file
final = deep_merge(defaults, request.config_json or {})
validated = ProjectConfig.model_validate(final)
project = Project(..., domain_key=domain_key, config_json=validated.model_dump())
# optional: seed project_prompts from fields/{domain}/prompts/
```

## Pharmacy benchmarks (manual / integration)

1. `كل الادوية المصنفة كباسط للعضلات` → all rows from FINALMEDICIN.xlsx
2. `عايز كل الادوية المتعارضة مع cordarone` → all interactions, stable on repeat
3. Prescription: Cordarone, Tryptizol, Averozolid, Lyrica, Alkapress → pairwise only if documented
4. `dimra استخدامات` then `الجرعة الخاصة به` → resolves Dimra from history

## Constraints

- Python 3.13, FastAPI, async I/O, type hints
- No provider imports in services beyond factories
- Unit + integration tests for changed behavior
- Do not commit secrets
- Minimize unrelated refactors
- Constitution: hybrid retrieval, reranker, citations, prompt versioning preserved

## Done when

- [ ] Phases A–D complete
- [ ] `pytest` passes
- [ ] Alembic migration applies clean
- [ ] New pharmacy project: `domain_key=pharmacy`, `config_json` populated from file
- [ ] PH-SC-001 … PH-SC-005 addressed or documented with test evidence

## Commands

```powershell
cd D:\mini-rag
# run tests
pytest tests/unit tests/integration -v
# migrations (inside docker or local venv per project setup)
```

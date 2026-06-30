# Research: Field Registry Architecture

**Feature**: `002-field-registry` | **Date**: 2026-06-29

## R1 — Why core files are bloated today

**Decision**: Domain logic is embedded in generic modules; refactor by **extraction**, not rewrite.

| File | ~Lines | Domain logic embedded |
|------|--------|------------------------|
| `utils/retrieval.py` | ~570 | Legal article/chapter boosts, exhaustive patterns, comparison splits, pharmacy-none |
| `utils/structural_split.py` | ~215 | Chapter/article boundaries (legal) |
| `controllers/ProcessController.py` | ~190 | XLSX as one blob (pharmacy pain), PDF page logic |
| `controllers/NLPController.py` | ~600 | Expansion orchestration + structural enrichment calls |
| `services/RAGService.py` | ~270 | Query classification, focus_document_text, prompt assembly |
| `stores/llm/templates/.../rag.py` | ~80 each | Generic prompts only |

**Target after refactor**:

| File | Target ~Lines | Role |
|------|---------------|------|
| `core/retrieval/engine.py` | ~200 | RRF, hybrid_rrf, dedupe, merge — **no regex patterns** |
| `core/retrieval/classifier.py` | ~80 | Delegates to `FieldProfile.retrieval` |
| `core/chunking/engine.py` | ~120 | Splitter primitives |
| `controllers/NLPController.py` | ~350 | Orchestration only |
| `services/RAGService.py` | ~180 | Pipeline only |
| `utils/retrieval.py` | ~50 | **Deprecated shim** → re-export from core |

**Estimated reduction**: ~400–500 lines removed from core; ~300 lines moved to `fields/*/`.

---

## R2 — Field pack format

**Decision**: YAML per module + text prompts; JSON Schema validation at load time.

```text
src/fields/
├── registry.yaml
├── _schema/                    # JSON schemas for validation
├── generic/                    # fallback defaults
├── pharmacy/
└── legal/
```

**Why YAML not Python modules**: Non-developers can edit; no redeploy for prompt/pattern tweaks if hot-reload added later; constitution prefers config-driven behavior.

**Why not only DB**: Logic patterns belong in git-reviewed packs; DB holds project identity + overrides only.

---

## R3 — FieldProfile merge precedence

**Decision**:

```text
effective = merge(
  fields.generic.*,           # base
  fields[domain_key].*,       # domain
  project_domain_config.config_json,  # project
  project_prompts             # prompt text override
)
```

Project `config_json` keys are shallow-merge at top level; nested keys (e.g., `retrieval.patterns`) deep-merge one level.

---

## R4 — Loader and registry

**Decision**: `FieldRegistry` singleton loaded in `main.py` startup (like settings).

```python
class FieldRegistry:
    def get(self, domain_key: str) -> FieldPack: ...
    def build_profile(self, domain_key: str, project_overrides: dict) -> FieldProfile: ...
```

Cache parsed YAML in memory; reload only in dev with `FIELDS_HOT_RELOAD=true`.

---

## R5 — Migration strategy

**Decision**: Phased refactor — **strangler fig** pattern.

| Phase | Action | Risk |
|-------|--------|------|
| 1 | Add `fields/`, `FieldRegistry`, DB table; default `generic` | Low |
| 2 | Extract legal patterns to `fields/legal/`; core delegates | Medium |
| 3 | Extract `generic` defaults; slim `retrieval.py` | Medium |
| 4 | Add `fields/pharmacy/` (from 001); row chunking | Medium |
| 5 | Remove deprecated shims | Low |

Existing projects: Alembic migration adds `domain_key` + `config_json` columns on `projects` (default `generic`, `{}`). No extra table.

---

## R6 — Relationship to 001-pharmacy

**Decision**: `001` implementation **moves under** `fields/pharmacy/` after `002` Phase 1–3 complete.

| 001 artifact | Becomes |
|--------------|---------|
| `utils/pharmacy/classifier.py` | `fields/pharmacy/retrieval.yaml` + thin adapter |
| `PHARMACY_*` env vars | `fields/pharmacy/domain.yaml` + project overrides |
| Query rewrite service | `core/query_understanding.py` reads `FieldProfile` |

---

## R7 — Testing

**Decision**:

- `tests/unit/fields/test_registry.py` — load all packs, schema valid
- `tests/unit/fields/test_merge.py` — override precedence
- `tests/unit/fields/legal/test_retrieval_patterns.py` — pattern match from YAML
- `tests/unit/fields/pharmacy/test_chunking.py` — row strategy
- Regression: existing retrieval tests run with `generic` profile

---

## R8 — `structural_split` ownership

**Decision**: Legal-heavy; lives in `fields/legal/structural_split.yaml`. Generic pack provides no-op/minimal boundaries. Core `structural_split.py` becomes **engine** that reads patterns from profile:

```yaml
# fields/legal/structural_split.yaml
boundaries:
  - pattern: '(?:الفصل|الباب|مادة)\s+...'
    type: article
article_query_patterns: [...]
```

Pharmacy pack may omit this file → engine uses empty patterns.

---

## R9 — `chunk_metadata` ownership

**Decision**: Field-specific label formatting and extra metadata keys.

| Field | Extra metadata keys | Label format |
|-------|---------------------|--------------|
| generic | file_name, page | `file — page N` |
| pharmacy | row_index, sheet_name, brand_name | `file — row N` |
| legal | article_number, chapter | `file — مادة N` |

`format_source_label` moves to `core/chunk_metadata/engine.py` + profile format string.

---

## R10 — Open decisions (resolved)

| Question | Resolution |
|----------|------------|
| `fields/` at root vs `src/fields/` | `src/fields/` for co-location with imports |
| Python in field packs? | No in v1; optional `hooks.py` in v2 for complex logic |
| Admin UI | Out of scope; API endpoint `PATCH /projects/{id}/domain` in v1 |

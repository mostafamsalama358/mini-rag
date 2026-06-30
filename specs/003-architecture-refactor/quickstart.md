# Quickstart: Architecture Refactor (003)

**Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> This is a **validation runbook**, not an implementation guide. It tells you how to prove each phase kept behavior frozen (FR-001) and ended green (FR-011). Concrete code changes live in `tasks.md` (next phase). Full code bodies, migrations, and complete test suites are intentionally omitted.

## Prerequisites

- Python 3.13 (constitution-mandated runtime)
- PostgreSQL 15+ with the `pgvector` extension (or Docker Compose for local Postgres + broker)
- The repo on branch `003-architecture-refactor`, with `main` checked out locally as the **baseline** for the contract snapshot
- Project deps installed: `pip install -e .` (or the project's install command) so `pytest`, `ruff`, FastAPI, SQLAlchemy, Celery resolve

## One-time setup (before P1)

1. **Capture the baseline contract snapshot** from `main` (the frozen contract — see [contracts/frozen-behavior-contract.md](./contracts/frozen-behavior-contract.md)):
   ```bash
   git checkout main
   # generate the snapshot the contract test will compare against
   pytest tests/contract/ --snapshot-update   # once guards exist, or record manually
   git checkout 003-architecture-refactor
   ```
2. **Record the baseline green run** on `main`:
   ```bash
   pytest -q          # save the passing count — this is the bar every phase must meet
   ```
3. **Confirm oversized files exist** (so P2 has something to split):
   ```bash
   # list any src/ file over 400 SLOC (executable+declarations; excludes blanks/comments/docstrings)
   python -c "import pathlib,glob; [print(p) for p in glob.glob('src/**/*.py',recursive=True)]"
   ```

## Per-phase validation

Every phase ends with **the same three checks**. Do not advance until all pass.

### Check A — Suite green (FR-009)
```bash
pytest -q
# Expected: same passing count as the main-branch baseline, no assertion failures.
# Import-line changes in tests are allowed; assertion changes are NOT.
```

### Check B — Frozen contract (FR-001)
```bash
pytest tests/contract/ -q
# Expected: the route table, Celery task names/queues, Settings env vars, and
# Prometheus metric/label names all match the baseline snapshot (see contracts/).
```

### Check C — Layer boundaries (FR-007, NFR-001)
```bash
# Inner layers must not import from outer layers. Expected: zero hits.
# (run from repo root)
# Domain (core/, entities, enums, fields/) must not import presentation/application/infra:
```
Search the domain packages for any import of `routes`, `services`, `repositories`, `stores`, `utils`, `tasks` — there must be none. (A scripted grep is in `tasks.md`.)

## Phase-by-phase acceptance

### Phase 1 — Renames & moves
**Scope**: `controllers/`→`services/` (merge), `models/*Model.py`→`repositories/`, `utils/pharmacy_compat.py`→`fields/pharmacy/`.

**Validate**:
- Check A, B, C above.
- `src/controllers/` no longer exists; its classes importable from `services/`.
- `src/repositories/` exists; `src/models/` contains only `db_schemes/` + `enums/` (+ `__init__`).
- `src/ARCHITECTURE.md` path references updated to match.

### Phase 2 — Oversized-file splits
**Scope**: `NLPController`+`RAGService`→`services/rag/*`; `core/retrieval/engine.py`→`core/retrieval/*`; `PGVectorProvider.py`→`stores/vectordb/providers/pgvector/*`.

**Validate**:
- Check A, B, C above.
- Size check: no `.py` under `src/` exceeds 400 SLOC:
  ```bash
  # Expected: empty output (no offenders)
  ```
- `_validate_identifier` and `_IDENTIFIER_RE` exist verbatim in the pgvector split (security invariant, NFR-007).
- RAG pipeline still emits the same metrics at the same stages (Check B observability).

### Phase 3 — Deduplication
**Scope**: delete `utils/retrieval.py` + `utils/structural_split.py`; migrate callers to `core.*`; consolidate `flowerconfig.py`.

**Validate**:
- Check A, B, C above.
- `grep` for `from utils.retrieval import` and `from utils.structural_split import` → **zero** hits across `src/` and `tests/`.
- Exactly one `flowerconfig.py` remains; `docker/docker-compose.yml` references the surviving copy.

### Phase 4 — Docs sync + contract guard
**Scope**: sync `ARCHITECTURE.md`, `docker-compose.yml`, `AGENTS.md`; add `tests/contract/`.

**Validate**:
- Check A, B, C above.
- Every path mentioned in `src/ARCHITECTURE.md` exists on disk.
- `tests/contract/test_frozen_contract.py` passes against the baseline snapshot.

## End-to-end smoke (optional, post-P4)

If a live stack is available, confirm the user-visible journey is unchanged:
1. Start services via Docker Compose.
2. Create a project, upload a file, trigger indexing (`/api/v1/nlp/index/push/{id}`).
3. Ask a RAG question (`/api/v1/nlp/index/answer`) and confirm the answer + citations format matches a pre-refactor capture.

## Expected final outcome

- All 4 phase checks green.
- 0 files over 400 SLOC.
- A reviewer can locate (a) HTTP handlers, (b) RAG orchestration, (c) data access, (d) DB entities, (e) provider wiring from names/folders alone (Success Criterion SC-006).

# Scope Guard Checklist (018)

**Purpose**: Prevent architecture tasks from absorbing out-of-scope work.

## MUST remain out of this feature’s execution

- [x] No retrieval/answer pipeline implementation code
- [x] No algorithms, formulas, thresholds, or pseudocode as normative design
- [x] No provider/model selection as architecture winners
- [x] No class diagrams or sprint coding plans as deliverables of 018 architecture phase
- [x] No ADRs authored under 018 (plan Out of Scope)
- [x] No second retrieval or answer path
- [x] No redefinition of Feature 014 golden metrics
- [x] No coupling to Feature 017 ingest job lifecycle entities
- [x] No physical package/folder “winners”

## MUST remain in scope

- [x] Governance registries and indexes under `governance/`
- [x] Review checklists under `checklists/`
- [x] Architecture tests under `tests/architecture/test_018_*.py`
- [x] Doc cross-links in `AGENTS.md` / `src/ARCHITECTURE.md` (logical owners only)

**Verdict**: Scope guard documented for polish verification (T060).

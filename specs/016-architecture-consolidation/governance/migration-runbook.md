# Migration Runbook (M0–M8)

**Feature**: 016-architecture-consolidation  
**Rule**: Cutover before retirement (P11). Retirement phases MUST NOT open before sole-owner phases for the same concern.

| Phase | Name | Outcome | Exit gate category | Predecessor |
|-------|------|---------|--------------------|-------------|
| M0 | Freeze dual-path growth | No new parallel production implementations | Architecture / Process | — |
| M1 | Answer sole owner | One user-visible Answer path | Runtime + Operational | M0 |
| M2 | Retrieval sole owner | One retrieval-execution Owner for Answer; Search interim ownership explicit | Architecture + Runtime | M1 |
| M3 | Contract unification | One production contract per shared concept | Architecture + Code | M2 |
| M4 | Ingest/chunking sole path | One parse→chunk ownership model; one embed-text policy owner | Runtime + Code | M3 |
| M5 | Dependency direction | Core free of concrete infrastructure dependencies | Code + Architecture | M4 |
| M6 | Domain extraction | Vertical heuristics owned by Domain Packs | Architecture + Code | M5 |
| M7 | Retirement wave | Retire After Cutover + transitional diagnostics cleared from production | Code + Operational | M1–M6 sole-owner gates for concerns being retired |
| M8 | Lifecycle resolution | Pending/Dormant/Research honestly labeled, activated, or archived | Architecture + Process | M7 |

## Phase detail

### M0
See [`m0-freeze.md`](./m0-freeze.md).

### M1
Checklist: [`../checklists/m1-answer-sole-owner.md`](../checklists/m1-answer-sole-owner.md). Vehicle: 015.

### M2
Checklist: [`../checklists/m2-retrieval-sole-owner.md`](../checklists/m2-retrieval-sole-owner.md). Interim search: [`search-interim-ownership.md`](./search-interim-ownership.md).

### M3
Contract roles unique in [`contract-role-catalog.md`](./contract-role-catalog.md); duplicate production contracts forbidden.

### M4
Checklist: [`../checklists/m4-ingest-chunking-sole-owner.md`](../checklists/m4-ingest-chunking-sole-owner.md). Re-index: [`reindex-compatibility.md`](./reindex-compatibility.md).

### M5
Core concerns depend on infrastructure **interfaces only** (`contracts/dependency-boundaries.md`).

### M6
Checklist: [`../checklists/m6-domain-extraction.md`](../checklists/m6-domain-extraction.md).

### M7
Checklist: [`../checklists/m7-retirement-wave.md`](../checklists/m7-retirement-wave.md) + [`../checklists/retirement-gate.md`](../checklists/retirement-gate.md). Rollback drill: [`rollback-drill.md`](./rollback-drill.md).

### M8
Checklist: [`../checklists/m8-lifecycle-resolution.md`](../checklists/m8-lifecycle-resolution.md).

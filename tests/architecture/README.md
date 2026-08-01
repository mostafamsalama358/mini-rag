# Architecture test suite (016 + 018 + 019 + 020 + 021)

Validates governance artifacts under:

- `specs/016-architecture-consolidation/governance/`
- `specs/018-rag-quality-architecture/governance/`
- `specs/019-rag-evaluation-framework/governance/`
- `specs/020-pharmacy-recommendation/` (ADR-020-001, frozen `/answer`, no Recommendation Service/API)
- `specs/021-domain-skill-framework/` (ADR-021-001, no Skill Service/API, frozen `/answer` response, SkillFilterProfile vs chunk MetadataProfile, no embedded Skill filters)

## Run

From repository root (with project venv / deps available):

```bash
pytest tests/architecture -q
pytest tests/architecture/test_018_*.py -q
pytest tests/architecture/test_019_*.py -q
pytest tests/architecture/test_020_*.py -q
pytest tests/architecture/test_021_*.py -q
```

## Mapping to validation categories

| Category | 016 | 018 | 019 | 020 | 021 |
|----------|-----|-----|-----|-----|-----|
| Architecture | ownership completeness | stage ownership, Context/Trace | metric ownership, profiles | ADR-020-001 capability-only | ADR-021-001 capability-only |
| Compatibility | lifecycle honesty | 014 non-redefinition | non-ownership freeze | frozen `/answer` fields | frozen `/answer` response fields |
| Process | governance checklist | quality-architecture-review | evaluation-architecture-review | architecture-review + recommend metric catalog | no skill detection; SkillFilterProfile ≠ MetadataProfile |
| Pack authoring | domain pack ownership | — | — | recommend pack files | skills/profiles YAML; no embedded filters |

Runtime/Operational cutover drills remain documented in each feature’s `quickstart.md`.

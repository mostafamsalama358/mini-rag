# Pharmacy Recommend Pack Files

Domain Pack extension for Feature 020. Loaded by `recommend_pack.py` (not a new FieldRegistry owner).

| File | Role |
|------|------|
| `symptom_taxonomy.yaml` | Controlled symptom/need taxonomy |
| `indication_tags.yaml` | Indication vocabulary + product seed tags |
| `recommendation_policy.yaml` | Ranking weights, bounds, clarification threshold |
| `safety_model.yaml` | Extensible safety dimensions (v1 subset active) |
| `parser.yaml` | Recommend intent rules (extended) |
| `answer_generation.yaml` | Recommend / compare explanation modules |

See `specs/020-pharmacy-recommendation/plan.md` and ADR-020-001.

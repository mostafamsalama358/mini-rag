# Contract: Query Understanding under Skills

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26  
**Authority**: Features 004 / 018 / 020; [spec.md](../spec.md) FR-010

---

## Mode: Skill-bound parse

**When**: Request carries a resolved `skill_id` for a Skill-enabled domain.

### MUST

- Extract entities / slots needed by Skill validation (e.g. medicines).
- Ground entities against project catalog when configured.
- Populate Need Frame **only** if Skill declares `capabilities.recommend_mode`.
- Emit clarification when validation rules fail (missing medicine pair, etc.).

### MUST NOT

- Predict or override Skill from text.
- Predict `field` / intent / skill for capability routing (Skill injects these).
- Run alias→skill or command detection.
- Auto-set `recommend_mode` from free-text need phrasing when Skill is not recommend-capable.

---

## QueryPlan authority split

| Field | Authority under Skill |
|-------|------------------------|
| `entities` / `entity` | Parser + grounding |
| `need_frame` | Parser when Skill.recommend_mode |
| `field` | **Skill binding** |
| `operation` | **Skill binding** |
| `recommend_mode` | **Skill binding** |
| `filters` (plan) | Merged with profile filters downstream; parser MUST NOT invent skill filters |

---

## Mode: No Skill registry

Domains with empty/absent Skill registry keep prior Query Understanding behavior (backward compatible) until a registry is published.

---

## Acceptance

- Same surface text under `interactions` vs `dosage` yields different Skill-injected `field`, comparable entity extraction.
- Architecture test: no code path maps retrieval.yaml intents → skill_id for Skill-enabled domains.

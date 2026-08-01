# Contract: Compatibility (015 / 016 / 020 / 004)

**Feature**: 021-domain-skill-framework | **Date**: 2026-07-26

---

## Feature 015 — Unified Pipeline / API Stability

| Surface | Rule |
|---------|------|
| Response fields | Frozen — Skills MUST NOT rename/remove `signal`, `answer`, `needs_clarification`, `full_prompt`, `chat_history` |
| Request fields | Additive `skill_id` allowed; existing fields keep names/defaults |
| Dual-run | Skills configure sole path only; not a second answer stack |

---

## Feature 016 — Architecture Consolidation

| Rule | Application |
|------|-------------|
| M0 freeze | No parallel Skill production path |
| Sole owners | No new Skill Execution owner ([ADR-021-001](../governance/adr-021-001-skills-as-domain-pack-capability.md)) |
| Domain packs | Skills/profiles extend 002 packs |

---

## Feature 004 — Semantic Query Parser

| Before (Skill-enabled) | After |
|------------------------|--------|
| Parser predicts field/intent for routing | Skill injects field/operation; parser extracts entities |
| Recommend intent from text | Only via recommend-capable Skill |

Non-Skill domains may retain prior behavior until registries land.

---

## Feature 020 — Pharmacy Recommendation

| Rule | Application |
|------|-------------|
| Capability preserved | Ranking, safety, explanation policies still apply |
| Entry point | Explicit Skill (`alternatives` / pack-declared recommend Skills) |
| Forbidden | Auto `recommend_mode` from free text on Skill-enabled pharmacy |

---

## Feature 018 / 019

- Skill id + profile id on Quality Trace / diagnostics.
- Skill-scoped golden sets and gates are 019’s implementation concern; this feature only requires attribution hooks.

---

## Ingest / chunk metadata

- No change to stored chunk metadata schema required for v1.
- Profiles consume existing `field` / `source` (and related) keys.
- Enrichment remains `chunk_metadata.yaml` / existing `MetadataProfile` type.

---

## Acceptance

- Contract tests: success response keys ⊆ 015 frozen set.
- Architecture tests: no recommend auto-intent path when pharmacy skills loaded.

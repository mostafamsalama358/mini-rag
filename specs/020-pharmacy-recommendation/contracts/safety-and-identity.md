# Contract: Safety Model and Product Identity

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

---

## Safety Model

### Dimension catalog

Pregnancy, Breastfeeding, Pediatric, Elderly, Renal impairment, Hepatic impairment, Diabetes, Hypertension, Contraindications, Interaction Severity, OTC / Prescription.

### Rules

1. SafetyLabel is **extensible**; new dimensions do not create a new owner or parallel path.
2. **v1 MAY implement a subset** (expected: pregnancy + breastfeeding first).
3. Missing label on a declared constraint dimension ⇒ **unknown**, not safe.
4. Safety Filtering runs **before** final user-facing recommendation presentation.
5. Outcomes: pass / demote / exclude / unknown — feed Safety Fitness and Trace.
6. When only high-risk products match under declared population ⇒ refuse first-line recommend + consult posture.
7. Full interaction-graph reasoning is out of scope for v1; Interaction Severity used only when simple signals exist.

## Product Identity Rules

Hierarchy:

```text
Brand → Product Line → Strength → Package
```

| Rule | Statement |
|------|-----------|
| Hierarchy awareness | Identify at the most specific level justified by need + evidence |
| No false duplicates | Distinct lines/strengths with different indications/fields MUST NOT collapse solely for shared brand |
| No false independents | Package-only variants SHOULD NOT consume multiple recommend slots when package is irrelevant |
| Disambiguation | Prefer need-specific line; else group under brand with explicit line disambiguation |
| Eval alignment | Golden allow/forbid keys match presentation identity level |

## Ingest

Indication tags, SafetyLabel dimensions in use, and identity fields MUST be carryable through sole ingest/index metadata (006/017)—no second ingest path.

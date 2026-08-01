# Contract: Need Frame and Symptom Taxonomy

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

---

## Need Frame

1. Recommend-mode queries MUST be representable as a **NeedFrame** ([data-model](../data-model.md)).
2. All NeedFrame fields are **optional per query** unless pack policy marks a subset required for high-confidence recommend.
3. Supported optional attributes include: Normalized Need, Population, Severity, Duration, Acute/Chronic, Multiple Symptoms, Existing Diagnosis, Goal, Language, Confidence.
4. Low Confidence (below RecommendationPolicy threshold) MUST trigger clarify or refuse—not unconstrained guessing.
5. Multi-symptom / multi-need MUST NOT silently merge incompatible therapy classes; clarify or multi-frame handling required.

## Symptom Taxonomy

1. Mapping MUST use a **controlled taxonomy** (versioned Domain Pack artifact), not an ungoverned flat dictionary as sole authority.
2. MUST support: many-to-many mapping; hierarchical relationships; synonyms; Arabic/English normalization; future node expansion.
3. Ambiguous multi-bucket mappings MUST be detectable for clarification.
4. Taxonomy changes are pack-versioned; eval golden sets SHOULD pin taxonomy versions via 019 dataset governance when blocking.

## Intent

1. Pack/parser MUST distinguish recommend / need-based intent from pure single-entity field lookup and from verify-indication (brand+need) postures.
2. Brand+need (“is X good for acidity?”) MUST NOT be forced through open recommend when product-evaluation is the correct posture.

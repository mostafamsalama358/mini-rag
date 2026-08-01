# Data Model: Pharmacy Recommendation Capability

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

Logical entities for recommend-mode. No ORM schema, wire JSON for a new API, or persistence engine is prescribed. External user I/O remains the frozen `/answer` contract; these entities are internal / pack / trace / eval subjects.

---

## Entity Overview

| Entity | Purpose |
|--------|---------|
| NeedFrame | Optional structured need extracted for recommend-mode |
| SymptomTaxonomy | Controlled vocabulary + relations for need→indication mapping |
| TaxonomyNode | Node in the symptom/need taxonomy |
| IndicationTag | Controlled product indication label |
| ProductIdentity | Brand → line → strength → package identity |
| SafetyLabel | Extensible safety/constraint dimensions on a product |
| RecommendationCandidate | In-corpus candidate with signals and outcomes |
| RankingSignals | Named contributions to Recommendation Score |
| RecommendationScore | Policy-composed score (weights not fixed here) |
| RecommendationDecision | recommend / clarify / refuse / limited_coverage + ordered list |
| RecommendationPolicy | Versioned pack rules (bounds, weights, thresholds) |
| RecommendationTrace | Operator attribution record (018-aligned) |
| RecommendEvalCase | Golden item for 019 recommend profile |

---

## NeedFrame

| Field (logical) | Required | Meaning |
|-----------------|----------|---------|
| normalized_need | optional | Canonical need/symptom/condition key(s) |
| population | optional | Declared population context (e.g. pregnancy) |
| severity | optional | Subjective/clinical severity cue if present |
| duration | optional | Duration cue if present |
| acuity | optional | acute / chronic / unknown |
| multiple_symptoms | optional | List of symptom keys when multi-need |
| existing_diagnosis | optional | Stated diagnosis if present |
| goal | optional | User goal (relieve, prevent, …) if present |
| language | optional | User language (ar/en/…) |
| confidence | optional | Mapping/understanding confidence |
| raw_need_span | optional | Surface span(s) from query |

**Validation**: All fields optional per query; pack MAY mark subsets required for “high-confidence recommend.” Low confidence → clarify/refuse per policy.

---

## SymptomTaxonomy / TaxonomyNode

| Field (logical) | Meaning |
|-----------------|---------|
| taxonomy_id / version | Pack-governed identity |
| node_id | Stable node identity |
| labels_ar / labels_en | Surface forms |
| synonyms | Additional surface forms |
| indication_tags | Many-to-many linked IndicationTag ids |
| parents / children | Hierarchical broader/narrower links |
| clarification_prompt | Optional bounded clarification text |
| ambiguity_group | Optional group id for multi-bucket detection |

**Rules**: Many-to-many phrase↔tag; hierarchy may expand/constrain per policy; AR/EN normalize to same nodes when equivalent.

---

## IndicationTag

| Field (logical) | Meaning |
|-----------------|---------|
| tag_id | Stable controlled id |
| display_name | Human label |
| description | Optional clinical/scope note |
| active | Whether usable in matching |

Bound to products via ingest metadata; Domain Pack vocabulary.

---

## ProductIdentity

| Field (logical) | Meaning |
|-----------------|---------|
| brand | Brand head |
| product_line | Line within brand (e.g. migraine vs cold) |
| strength | Strength if relevant |
| package | Package/SKU if relevant |
| inn / generic | Optional substance identity |
| identity_level | Level used for ranking slot (brand\|line\|strength\|package) |

**Rules**: See [contracts/safety-and-identity.md](./contracts/safety-and-identity.md).

---

## SafetyLabel

Extensible dimension map. Each dimension holds a structured suitability/constraint value (enum-like: safe | use_with_caution | avoid | contraindicated | consult_physician | unknown — pack-defined).

| Dimension (catalog) | v1 expectation |
|---------------------|----------------|
| pregnancy | Likely implemented |
| breastfeeding | Likely implemented |
| pediatric | Future / optional |
| elderly | Future / optional |
| renal_impairment | Future / optional |
| hepatic_impairment | Future / optional |
| diabetes | Future / optional |
| hypertension | Future / optional |
| contraindications | As available from evidence/metadata |
| interaction_severity | As available |
| otc_prescription | Optional presentation signal |

**Rule**: Missing dimension ⇒ unknown (not safe).

---

## RecommendationCandidate

| Field (logical) | Meaning |
|-----------------|---------|
| candidate_id | Stable within decision |
| product_identity | Identity at chosen level |
| matched_indications | IndicationTag hits |
| evidence_pointers | Chunk/field/document refs |
| safety_outcome | pass \| demote \| exclude \| unknown + dimensions applied |
| ranking_signals | RankingSignals |
| recommendation_score | Policy-composed score |
| retained | Whether in final user-facing set |

---

## RankingSignals

| Signal | Meaning |
|--------|---------|
| indication_match | Taxonomy/tag fit strength |
| retrieval_evidence | Retrieved evidence support |
| reranker_confidence | Existing rerank signal when applied |
| safety_fitness | Posture after Safety Filtering |
| formulary_preference | Optional pack/project preference |

Absent signals are omitted from composition; Policy defines weights/enablement.

---

## RecommendationScore

| Field (logical) | Meaning |
|-----------------|---------|
| value | Policy-composed scalar or ordered key (implementation-defined later) |
| policy_version | Policy identity used |
| signal_breakdown | Per-signal contributions for operators |

**Non-normative**: Absolute numeric weight tables are **not** part of this data model identity.

---

## RecommendationDecision

| Field (logical) | Meaning |
|-----------------|---------|
| decision_type | recommend \| clarify \| refuse \| limited_coverage |
| ordered_candidates | Retained candidates after filter+rank |
| clarification_prompt | If clarify |
| policy_bounds_applied | Max/min truncation notes |
| language | Answer language |

Maps to frozen wire via answer text + existing clarification signals—not new response fields.

---

## RecommendationPolicy

| Field (logical) | Meaning |
|-----------------|---------|
| policy_id / version | Versioned pack (optional project override) |
| max_recommendations | Upper bound |
| min_recommendations | Optional success floor when coverage adequate |
| signal_weights / enabled_signals | Ranking composition |
| clarification_confidence_threshold | Below → clarify |
| prefer_higher_evidence | Boolean posture |
| prefer_safer_candidate | Boolean posture |
| language_policy_ref | Existing language policy |
| identity_presentation_rules | Slot/collapse rules |
| medical_advice_separation | Mandatory caveat posture |

---

## RecommendationTrace

| Field (logical) | Meaning |
|-----------------|---------|
| need_frame_summary | Redacted/summarized NeedFrame |
| taxonomy_mapping | Nodes/tags/confidence |
| constraints | Filters applied |
| candidates | Per-candidate matched indications, evidence pointers, safety outcome, rank contribution |
| decision | Decision type + bounds |
| correlation_id | Request correlation |

**Surface**: Quality Context / diagnostics (018)—not a breaking public `/answer` field.

---

## RecommendEvalCase (019 subject)

| Field (logical) | Meaning |
|-----------------|---------|
| query | Need-based query |
| language | ar/en |
| allow_list / forbid_list | Products at stated identity_level |
| graded_relevance | Optional for nDCG |
| safety_expectations | Exclude/demote expectations by dimension |
| expect_clarification | Boolean |
| slice_tags | domain=pharmacy, intent=recommend, … |

Lifecycle/governance of datasets follows Feature 019.

---

## Relationships

```text
NeedFrame —maps via→ SymptomTaxonomy —links→ IndicationTag —tags→ ProductIdentity
ProductIdentity —has→ SafetyLabel
Retrieval+Policy —yields→ RecommendationCandidate[] —ranked→ RecommendationDecision
RecommendationDecision + candidates —traced in→ RecommendationTrace
RecommendEvalCase —evaluates→ Decision/Candidates under 019 profiles
```

---

## State notes

- **Safety outcome**: unknown → demote/exclude/pass per policy (default conservative).
- **Decision**: clarify/refuse preferred over unsupported recommend when confidence or safety blocks.
- **No entity** implies a new HTTP resource.

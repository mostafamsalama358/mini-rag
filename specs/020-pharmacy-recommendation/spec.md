# Feature Specification: Pharmacy Recommendation Capability

**Feature Branch**: `020-pharmacy-recommendation`  
**Created**: 2026-07-22  
**Updated**: 2026-07-22  
**Status**: Draft  
**Input**: User description: "خطة recommendation قوية كـ Speckit feature رسمي — توصية أدوية من سؤال عرضي/حاجة علاجية داخل مسار الإجابة الحالي، مع بيانات indications، ترتيب مرشّحين، فلترة أمان، وتقييم، بدون owner جديد أو مسار إنتاج موازي"

## Summary

This feature defines a **pharmacy Domain Pack recommendation capability** so users can ask need-based questions (e.g. “دواء للحموضة؟”, “something for migraine headache”) and receive **grounded, ranked product recommendations** with safety caveats—using the **existing sole answer and retrieval path**, not a new production owner or parallel recommendation service.

Recommendation is a **capability extension** of Query Understanding → Retrieval Planning → Retrieval → Evidence → Context → Answer Generation, governed by Features **016** (sole-owner / M0 freeze), **018** (quality contracts), and **019** (evaluation). Structured indication and safety metadata on indexed products MUST be sufficient for candidate generation and filtering; leaflets and corpus workbooks remain the narrative and catalog sources until ingest contracts consume structured fields.

**Architecture decision (normative):** Recommendation remains a **Capability** under existing Retrieval + Answer ownership. See [ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md). No Recommendation Service, no Recommendation API, no parallel production path, no new sole owner.

---

## Relationship to Existing Features

| Feature | Relationship |
|---------|----------------|
| **016 Architecture Consolidation** | Binding. No new sole owner for “Recommendation.” No parallel production recommendation API or stage. Extension via Domain Pack + existing Answer/Retrieval owners. Exception ADR required if a dedicated owner is later proposed. Binding decision: [ADR-020-001](./governance/adr-020-001-recommendation-as-capability.md). |
| **015 Unified Pipeline Migration** | Frozen external `/answer` field-level contract remains. Recommendation MAY enrich answer **content** and internal quality/trace fields; MUST NOT rename or break frozen public response fields without a separate API contract change. |
| **018 RAG Quality Architecture** | Recommendation answers MUST satisfy claim grounding, evidence/context quality, and Quality Context/Trace expectations for recommend-mode answers. Candidate explainability and recommendation traces align with 018 diagnostic surfaces. |
| **019 RAG Evaluation Framework** | Offline/online recommendation eval profiles, golden sets, gates, and metric *implementation* live under 019 ownership; this feature defines *what* pharmacy recommendation quality means (including ranking and safety metrics catalog below). |
| **004 Semantic Query Parser** | Recommendation intent and Need Frames are Query Understanding concerns (pharmacy pack taxonomy). |
| **009 Retrieval Planner / 010 Retrieval Engine** | Candidate generation, hybrid retrieval, fusion, and reranking use existing planning and retrieval capabilities; indication-aware constraints and recommendation ranking compose on top—not a new engine owner. |
| **011 / 012 / 013** | Evidence, context, and answer composition remain sole path for recommend-mode outputs (ranked options + caveats + citations). Explanation policy constrains Answer Generation. |
| **002 Field Registry / Domain Packs** | Indication tags, symptom taxonomy, safety model, recommendation policy, and recommend answer policy are pharmacy Domain Pack extension points. |
| **006 Document Intelligence / 017 Ingest** | Structured indication/safety fields and product-identity metadata MUST be ingestible and indexed so retrieval can use them; no second ingest path. |

**Non-goals (explicit):**

- No standalone “recommendation microservice” or Recommendation Service.
- No dedicated Recommendation API or second answer endpoint as the production path.
- No new production pipeline or new sole owner for recommendation (logical flow only; see below).
- No free-form prescribing or dose calculation as a clinical decision system.
- No replacement of leaflet narrative with Excel-only answers until ingest + reindex gates pass.
- No new evaluation production stage inside the answer path (019 remains offline/online/monitoring architecture).
- No breaking change to frozen external `/answer` contracts (015 / ADR-003).

---

## Architecture Decision Record

**ADR-020-001 — Recommendation as Capability (not Service / API / parallel path)**  
Full text: [`governance/adr-020-001-recommendation-as-capability.md`](./governance/adr-020-001-recommendation-as-capability.md)

| Decision | Statement |
|----------|-----------|
| Capability | Recommendation is a Domain Pack **capability** exercised through the sole Answer + Retrieval architecture |
| No Recommendation Service | Must not introduce a standalone recommendation microservice or production owner module |
| No Recommendation API | Must not introduce a dedicated recommendation HTTP/API resource; user-visible output remains answer **content** under the frozen `/answer` contract |
| No parallel production path | Must not dual-run a second recommend pipeline alongside the sole path (M0 freeze / 016) |
| Ownership | Query understanding / Need Frame: existing Query Understanding concern; candidate retrieval & ranking signals: existing Retrieval owners; final recommend answer & explanation: existing Answer owner |
| Exception path | A dedicated Recommendation owner requires a **superseding exception ADR** under 016 — not implied by this feature |

---

## Logical Recommendation Flow *(not a new pipeline)*

Recommend-mode uses the **existing** sole production stages. The following is a **logical ordering of concerns** for specification and review—not a new pipeline, orchestrator, or deployable path:

```
Need (user query)
  ↓
Need Normalization
  ↓
Symptom Taxonomy Mapping
  ↓
Candidate Constraints (indication / identity / pack policy)
  ↓
Metadata Filtering (corpus-bounded product scope)
  ↓
Hybrid Retrieval (existing retrieval capability)
  ↓
Fusion (existing retrieval capability)
  ↓
Reranking (existing retrieval capability)
  ↓
Safety Filtering
  ↓
Recommendation Ranking (signal composition; see Ranking Model)
  ↓
Answer Generation (existing Answer owner + Explanation Policy)
```

**Normative clarifications:**

- This flow **composes** existing Query Understanding, Retrieval Planner, Retrieval Engine, Evidence, Context, and Answer Generation responsibilities.
- “Recommendation Ranking” is a **policy-governed scoring composition** over candidates already produced by retrieval—not a separate production stage owner.
- Skipping or collapsing steps when signals are absent is allowed (e.g. no formulary preference); inventing a parallel path is not.

---

## Recommendation Ranking Model

### Recommendation Score

Each **Recommendation Candidate** receives a **Recommendation Score** composed from explicit, named **signals**. Absolute numeric weights are **not** fixed in this specification; the **Recommendation Policy** (Domain Pack, versioned) defines signal weights, enablement, and tie-breaks later.

| Signal | Meaning (technology-agnostic) |
|--------|-------------------------------|
| **Indication Match** | Strength of fit between Need Frame / taxonomy-mapped indication tags and the candidate’s indication tags (including hierarchical/synonym expansion where applicable) |
| **Retrieval Evidence** | Support from retrieved evidence for the need (coverage, relevance of cited passages/fields) |
| **Reranker Confidence** | Confidence or rank signal from the existing reranking capability when applied |
| **Safety Fitness** | Fitness under Safety Filtering given declared population/context (safer and complete labels rank above unsafe or unknown when policy says so) |
| **Optional Formulary / Preference** | Optional pack or project preference (e.g. preferred line, availability flag)—disabled when not configured |

### Properties (normative)

- **Composable**: Score = policy-defined composition of the signals above (and only pack-approved additional signals if later ADRs allow).
- **Reviewable**: Operators and evaluators MUST be able to inspect which signals contributed to relative order (see Explainability).
- **Explainable**: Rank order MUST be attributable at candidate level in Recommendation Trace / Quality Context—without requiring end users to see hidden numeric scores.
- **No hidden sole criterion**: Ranking MUST NOT depend solely on an opaque model score with no inspectable signal breakdown for operators.
- **Evidence over vibes**: Indication Match and Retrieval Evidence MUST be first-class; generation MUST NOT invent rank order independent of these signals and Safety Filtering outcomes.
- **Product identity aware**: Ranking MUST respect Product Identity Rules (brand → line → strength → package) so SKUs are neither falsely treated as unrelated independents nor collapsed as duplicates when clinically distinct.

---

## Recommendation Policy

Versioned Domain Pack (and optional project overrides) **Recommendation Policy** governs recommend-mode behavior. Policy defines rules and thresholds; this spec states **rule categories**, not frozen numeric constants (unless already fixed elsewhere in platform language/citation policy).

| Rule category | Requirement |
|---------------|-------------|
| **Maximum recommendations** | Policy MUST define an upper bound on user-facing recommended options |
| **Minimum recommendations** | Policy MAY define a minimum for “successful” recommend answers when corpus coverage is adequate; otherwise clarify/limited-coverage applies |
| **Prefer higher evidence** | Candidates with stronger Retrieval Evidence / Indication Match SHOULD rank above weakly supported peers, all else equal |
| **Prefer safer candidate** | Given comparable need fit, safer Safety Fitness SHOULD outrank less safe or unknown when population constraints are present |
| **Never recommend out-of-corpus products** | Hard rule; aligns with FR-009 |
| **Always provide citations** | Hard rule for retrieval-backed recommend claims; aligns with constitution / NFR-004 |
| **Clarify instead of guessing** | When Need Frame / taxonomy confidence is below policy threshold, clarify or refuse broad recommendation |
| **Respect language policy** | Answer language follows user language (AR/EN) per existing platform language policy |
| **Respect product identity** | Present and rank at the clinically appropriate identity level (line vs strength vs package) per Product Identity Rules |
| **Separate recommendation from medical advice** | Answers MUST NOT claim licensed prescribing authority; consult caveats apply per Explanation Policy |
| **Signal weights** | Policy owns Recommendation Score weights and enabled signals; changes are versioned |

---

## Recommendation Explanation Policy

Applies to Answer Generation in recommend-mode (existing Answer owner):

1. The LLM (or composer) **explains using retrieved evidence only**.
2. Explanations MUST NOT cite or invent justifications from **hidden scores**, internal weights, or unaudited model intuition.
3. Explanations MUST NOT **fabricate reasons** (indications, safety claims, comparisons) absent from evidence or structured labels.
4. Explanations MUST NOT claim **clinical superiority** between products without evidence support for that claim.
5. Answers MUST **distinguish recommendation (corpus-bounded decision support)** from **medical advice / prescribing**.
6. User-facing text MAY state qualitative fit (“matches acidity indications in sources”) but MUST NOT dump internal rank contribution numbers to end users.
7. Uncertainty and “consult pharmacist/physician” posture remain mandatory when evidence or Safety Labels are incomplete.

---

## Product Identity Rules

Pharmacy products in corpus often form families. Ranking and presentation MUST use a clear identity hierarchy:

```
Brand
  ↓
Product Line
  ↓
Strength
  ↓
Package
```

| Rule | Statement |
|------|-----------|
| **Hierarchy awareness** | Candidates SHOULD be identified at the most specific level justified by Need Frame and evidence (e.g. migraine line vs generic brand head). |
| **No false duplicates** | Distinct lines/strengths that differ in indication tags or clinically relevant fields MUST NOT be collapsed as one duplicate solely because they share a brand. |
| **No false independents** | Near-identical SKUs that differ only by package (when package is irrelevant to the need) SHOULD NOT consume multiple recommendation slots as if unrelated therapies. |
| **Disambiguation** | When multiple lines share a brand, prefer the need-specific line when tags distinguish; otherwise group under brand with explicit line disambiguation in the answer. |
| **Eval alignment** | Golden allow/forbid lists SHOULD key off the identity level used in presentation (line vs brand) to avoid false failures. |

---

## Symptom Taxonomy

Symptom / need mapping is a **controlled taxonomy**, not a flat phrase→tag dictionary.

| Property | Requirement |
|----------|-------------|
| **Controlled vocabulary** | Taxonomy nodes and indication tags are Domain Pack–governed and versioned |
| **Many-to-many mapping** | One user phrase MAY map to multiple indication tags; one tag MAY be reachable from many phrases |
| **Hierarchical relationships** | Parent/child (or broader/narrower) relations MAY expand or constrain candidate matching per policy |
| **Synonyms** | Synonym sets (including colloquial forms) normalize to taxonomy nodes |
| **Arabic / English normalization** | AR and EN surface forms normalize to the same nodes where clinically equivalent |
| **Future expansion** | New nodes/relations MAY be added without changing ownership or introducing a parallel path |
| **Ambiguity** | Multi-bucket or low-confidence mappings trigger clarification per Recommendation Policy |

---

## Safety Model

**Safety Label** is an **extensible** structured model used by Safety Filtering and Safety Fitness. It is not limited to pregnancy/breastfeeding.

### Dimensions (catalog)

| Dimension | Role |
|-----------|------|
| Pregnancy | Suitability / constraint for pregnancy context |
| Breastfeeding | Suitability / constraint for lactation context |
| Pediatric | Suitability / constraint for pediatric populations |
| Elderly | Suitability / constraint for elderly populations |
| Renal impairment | Suitability / constraint when renal impairment is declared |
| Hepatic impairment | Suitability / constraint when hepatic impairment is declared |
| Diabetes | Constraint or caution when diabetes context is declared |
| Hypertension | Constraint or caution when hypertension context is declared |
| Contraindications | Explicit contraindication signals relevant to need or population |
| Interaction Severity | Severity signals for concurrent-therapy constraints when available |
| OTC / Prescription | Supply classification signal for presentation/policy (not a legal oracle) |

### Normative rules

- **v1 MAY implement a subset** (e.g. pregnancy + breastfeeding first) without removing other dimensions from the model catalog.
- Missing labels ⇒ **unknown**, not “safe”; Explanation Policy requires caveat / consult.
- Safety Filtering runs **before** final user-facing recommendation presentation; outcomes feed Safety Fitness and Recommendation Trace.
- Expanding dimensions later MUST NOT create a new owner or parallel path—pack + ingest metadata only.

---

## Candidate Explainability

For every Recommendation Candidate considered in recommend-mode, operators (via Quality Context / Recommendation Trace—not a breaking public API) MUST be able to determine:

| Attribute | Meaning |
|-----------|---------|
| **Matched Indications** | Which taxonomy / indication tags matched the Need Frame |
| **Retrieved Evidence** | Which evidence pointers supported inclusion |
| **Safety Outcome** | Filter result (pass / demote / exclude / unknown) and applicable dimensions |
| **Rank Contribution** | Which ranking signals contributed to relative order (reviewable breakdown) |

**End-user boundary:** Internal prompts, raw hidden model scores, and weight tables MUST NOT be required in the user-facing answer. User-facing text follows Explanation Policy (evidence-backed qualitative rationale + citations).

---

## Evaluation Metrics *(defined here; implemented under Feature 019)*

This feature defines the **metric catalog** for pharmacy recommend-mode quality. **Feature 019 owns implementation**, profiles, judges, gates, and run metadata. No production evaluation stage is added to the answer path.

| Metric | Intent |
|--------|--------|
| **Recall@K** | Fraction of relevant allow-listed products appearing in top-K recommendations |
| **Precision@K** | Fraction of top-K recommendations that are relevant per golden |
| **MRR** | Mean reciprocal rank of first relevant recommendation |
| **nDCG** | Graded ranking quality of the recommended list |
| **Safety Precision** | Among safety actions taken (exclude/demote), fraction that were correct per golden |
| **Safety Recall** | Among products that should have been excluded/demoted, fraction correctly handled |
| **False Recommendation Rate** | Rate of recommending out-of-corpus, forbidden, or fabricated products |
| **Clarification Rate** | Rate of clarification / limited-coverage outcomes on designated ambiguous or low-confidence cases |
| **Corpus-Boundedness** | Rate of recommend answers whose recommended products are all in-corpus |
| **Recommendation Diversity** | Spread across distinct therapy lines / identity levels where golden expects non-redundant options (policy-defined) |

Defect attribution MUST distinguish at least: taxonomy/tag miss, retrieval miss, safety-filter error, ranking error, and generation/explanation hallucination (018/019).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for a medicine by need (Priority: P1)

A pharmacy user or clinician asks in Arabic or English for a medicine for a symptom or condition (e.g. acidity, headache, migraine, diarrhea) **without naming a brand**. The system returns a **short ranked list of in-corpus products** that match the need, with brief grounded reasons and citations, and states uncertainty when the corpus is thin.

**Why this priority**: This is the primary gap versus today’s entity-centric Q&A; it is the MVP that makes “دواء للحموضة؟” useful.

**Independent Test**: With a project whose indexed products carry indication tags for acidity/PPI/antacid (or equivalent), ask an acidity need question with no brand; assert recommend-mode answer with ≥1 cited in-corpus candidate and no invented out-of-catalog drugs.

**Acceptance Scenarios**:

1. **Given** indexed products with indication coverage for acidity, **When** the user asks “دواء للحموضة؟”, **Then** the answer recommends in-corpus options (e.g. PPI and/or antacid lines present in the project), cites sources, and does not invent brands absent from the corpus.
2. **Given** the same corpus, **When** the user asks “medicine for migraine headache”, **Then** migraine-relevant in-corpus products are preferred over unrelated cold/flu combos when tags and evidence support that distinction.
3. **Given** insufficient indication evidence for the need, **When** the user asks a need-based question, **Then** the system clarifies or states limited coverage rather than fabricating recommendations.

---

### User Story 2 - Safety-aware recommendations (Priority: P1)

The same user adds population or clinical context constraints (e.g. pregnancy, breastfeeding, pediatric, elderly, organ impairment, or comorbidity signals when available in the Need Frame). Recommendations MUST exclude or demote contraindicated or high-risk options per the extensible Safety Model and surface caveats in the answer language.

**Why this priority**: Unsafe recommendations are worse than no recommendation; safety is a hard gate for pharmacy.

**Independent Test**: Ask for a pain/fever medicine while stating pregnancy; assert products labeled avoid/contraindicated for pregnancy are not presented as preferred first-line without explicit contraindication messaging. v1 may assert on the implemented Safety Model subset.

**Acceptance Scenarios**:

1. **Given** pregnancy context and products with pregnancy safety labels, **When** the user asks for a painkiller, **Then** avoid/contraindicated options are filtered or clearly labeled as unsuitable; safer labeled options are preferred when present.
2. **Given** no reliable safety label for a candidate on a declared dimension, **When** that candidate would otherwise rank highly, **Then** the answer includes an explicit uncertainty/consult caveat rather than implying clinical clearance.
3. **Given** a need that only matches high-risk products for the stated population, **When** recommendation runs, **Then** the system refuses first-line recommendation and advises professional consultation.
4. **Given** a future-enabled dimension (e.g. renal impairment) with labels present, **When** that constraint appears in the Need Frame, **Then** Safety Filtering applies the same exclude/demote/unknown posture without requiring a new recommendation owner.

---

### User Story 3 - Ambiguous need clarification (Priority: P2)

When the need is too broad or maps via the Symptom Taxonomy to multiple clinical buckets (e.g. “stomach problem”, “cold”), the system asks a **bounded clarification** (or returns a structured clarification payload consistent with existing answer behavior) before or instead of a wide unfocused list.

**Why this priority**: Reduces wrong-bucket recommendations; improves trust.

**Independent Test**: Ask an underspecified need; assert clarification or scoped options, not a long undifferentiated dump of unrelated ATC classes.

**Acceptance Scenarios**:

1. **Given** an ambiguous symptom phrase with multi-bucket taxonomy mapping, **When** recommend intent is detected, **Then** the user receives a short clarification question or narrowly scoped option groups tied to corpus coverage.
2. **Given** the user answers the clarification, **When** recommendation continues, **Then** candidates align with the clarified Need Frame.

---

### User Story 4 - Compare or choose among need-matched options (Priority: P2)

After candidates are identified, the user asks which option is better for their need (or the system presents a concise comparison). The answer compares **on need-relevant fields** (indication fit, key safety, notable interactions) using retrieved evidence—not marketing language, hidden scores, or unsupported clinical superiority.

**Why this priority**: Natural follow-on to P1; reuses multi-entity compare strengths.

**Independent Test**: From an acidity recommendation set, ask to compare two returned products on suitability for heartburn; assert field-grounded compare with citations.

**Acceptance Scenarios**:

1. **Given** two acidity-tagged products in context, **When** the user asks which is better for heartburn, **Then** the answer compares using retrieved clinical fields, follows Explanation Policy, and remains in recommend/compare posture without inventing superiority claims beyond evidence.
2. **Given** only one strong candidate, **When** compare is requested, **Then** the system states limited comparison basis rather than inventing peers.

---

### User Story 5 - Evaluation and regression gates for recommendation (Priority: P2)

Quality owners and engineers run **offline recommendation evaluation** (and optional online/shadow signals) so recommend-mode changes cannot ship without gates on ranking quality, safety correctness, grounding/corpus-boundedness, clarification behavior, and language—using the metric catalog herein under Feature 019.

**Why this priority**: Prevents silent regressions as tags and prompts evolve; aligns with 019.

**Independent Test**: A documented recommendation golden set and 019 profile can be executed offline; failing safety, corpus-boundedness, or grounding gates blocks “recommend ready” status.

**Acceptance Scenarios**:

1. **Given** a pharmacy recommendation golden set, **When** an offline eval profile runs, **Then** metrics (including Recall@K / Precision@K / safety metrics / False Recommendation Rate / Corpus-Boundedness as profiled) distinguish taxonomy/retrieval misses from ranking errors, answer hallucination, and safety-filter failures.
2. **Given** a change that recommends an out-of-corpus drug, **When** gates run, **Then** the run fails Corpus-Boundedness / False Recommendation Rate criteria.

---

### User Story 6 - Operator visibility into recommend decisions (Priority: P3)

Operators inspecting a recommend-mode answer can see **why** candidates were included/excluded and how they ranked (Need Frame, matched indications, evidence pointers, safety outcomes, rank contribution signals) via quality/trace surfaces—without exposing a new public breaking API and without dumping hidden scores to end users.

**Why this priority**: Debugging and trust; secondary to user-facing MVP.

**Independent Test**: For a filtered pregnancy case, Recommendation Trace / quality context shows exclusion reason and matched indications for at least one candidate; rank contribution signals are present for retained candidates.

**Acceptance Scenarios**:

1. **Given** a recommend-mode answer with safety filtering, **When** an operator inspects allowed diagnostics/quality context, **Then** inclusion/exclusion rationales and rank contribution signals are attributable at candidate level per Candidate Explainability.

---

### Edge Cases

- Need phrase with **no** matching taxonomy nodes and weak lexical retrieval → clarify or “not enough corpus coverage,” do not invent drugs.
- User names a **brand + need** (“is X good for acidity?”) → treat as product-evaluation / verify-indication, not open recommend—or hybrid with explicit product focus.
- **Multiple symptoms** or multi-need questions (“acidity and constipation”) → populate Need Frame multi-symptom fields or clarify; do not merge incompatible therapy classes silently.
- **Severity / duration / acute-vs-chronic / existing diagnosis / goal** present in query → optional Need Frame fields MAY refine constraints; absence MUST NOT block recommend-mode.
- **Pediatric / elderly / organ impairment / comorbidity** mentions without structured labels → conservative caveat + consult; do not overclaim.
- **Interaction-only** constraints without a need → not recommend-mode; existing interaction Q&A applies.
- Corpus contains **product families** (e.g. multiple Panadol lines/SKUs) → apply Product Identity Rules (prefer need-specific line; avoid false duplicate slots for package-only variants).
- Answer language MUST follow the user language (Arabic/English) per existing language policy.
- Empty project / zero indexed chunks → existing empty-retrieval behavior; no fake recommendations.
- Ranking signals partially unavailable (e.g. no formulary preference) → compose over available signals; do not invent a parallel path.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect **recommend / suggest-therapy / need-based** intent (and related verify-indication intent) as part of pharmacy query understanding, distinct from pure single-entity field lookup.
- **FR-002**: System MUST represent a **Need Frame** for recommend-mode queries. Fields are **optional per query** and MAY include: Normalized Need; Population; Severity; Duration; Acute/Chronic; Multiple Symptoms; Existing Diagnosis; Goal; Language; Confidence (see Key Entities).
- **FR-003**: Indexed pharmacy products MUST be associable with **indication tags** (controlled vocabulary) usable for candidate generation; tags MUST be Domain Pack–governed and project-corpus–bounded.
- **FR-004**: System MUST maintain a pharmacy Domain Pack **Symptom Taxonomy** (not a flat dictionary) supporting many-to-many mapping, hierarchical relationships, synonyms, Arabic/English normalization, and future expansion, so natural-language needs resolve to retrieval/candidate constraints.
- **FR-005**: For recommend-mode, the sole retrieval path MUST be able to generate a **bounded candidate set** of in-corpus products using indication tags and/or need-aware retrieval—not unrestricted open-web drug lists—following the Logical Recommendation Flow without creating a new pipeline.
- **FR-006**: System MUST compute a **Recommendation Score** from named signals (Indication Match, Retrieval Evidence, Reranker Confidence, Safety Fitness, optional Formulary/Preference). Weights and enablement are owned by Recommendation Policy; ranking MUST be reviewable and explainable.
- **FR-007**: System MUST apply **Safety Filtering** before final recommendation presentation using the extensible Safety Model; v1 MAY use a subset of dimensions. Unknown MUST NOT be treated as safe.
- **FR-008**: Recommend-mode answers MUST be produced by the **existing Answer owner** path under Recommendation Explanation Policy: ranked options, evidence-only rationale, citations, and mandatory uncertainty/consult caveats when evidence or safety labels are incomplete.
- **FR-009**: Recommend-mode answers MUST NOT present out-of-corpus products as available recommendations.
- **FR-010**: When Need Frame / taxonomy confidence is below a pack-defined threshold, system MUST clarify or refuse broad recommendation rather than guess the clinical bucket.
- **FR-011**: Frozen external answer API field names and shapes MUST remain stable; recommendation behavior changes content and internal quality/trace, not breaking public contract fields (unless a separate versioned API change is explicitly approved).
- **FR-012**: System MUST support Arabic and English need phrasings via Symptom Taxonomy normalization for the pharmacy pack.
- **FR-013**: Recommendation quality MUST be evaluable under Feature 019 via a dedicated pharmacy recommendation profile/golden set covering the Evaluation Metrics catalog herein (ranking, safety, corpus-boundedness, clarification, diversity as profiled).
- **FR-014**: Recommendation Trace / Quality Context for recommend-mode MUST record Need Frame summary, candidate set summary, matched indications, evidence pointers, safety outcomes, and rank contribution signals sufficient for defect attribution (018/019) and Candidate Explainability.
- **FR-015**: Ingest/indexing MUST be able to carry indication tags, Safety Labels, and product-identity metadata (brand/line/strength/package as applicable) into retrievable product/chunk metadata so recommend-mode does not depend on prompt-only memorization.
- **FR-016**: M0 freeze / ADR-020-001: this feature MUST NOT introduce a Recommendation Service, Recommendation API, parallel production recommendation path, or a new sole owner without a superseding exception ADR under 016.
- **FR-017**: System MUST apply **Product Identity Rules** so ranking and presentation neither falsely duplicate package-only SKUs nor incorrectly merge distinct lines/strengths.
- **FR-018**: System MUST enforce **Recommendation Policy** rule categories (max/min recommendations, prefer higher evidence, prefer safer candidate, corpus-boundedness, citations, clarify-instead-of-guessing, language, identity, medical-advice separation). Policy owns numeric thresholds and signal weights.
- **FR-019**: End-user answers MUST NOT expose internal prompts or require hidden score dumps; operator explainability remains on allowed diagnostic/trace surfaces only.

### Key Entities *(include if feature involves data)*

- **Need Frame**: Structured representation of a recommend-mode user need. **Attributes (all optional per query unless pack marks required):** Normalized Need; Population; Severity; Duration; Acute/Chronic; Multiple Symptoms; Existing Diagnosis; Goal; Language; Confidence. Produced by Query Understanding; consumed by mapping, constraints, and filtering.
- **Indication Tag**: Controlled label on a product (e.g. acidity, migraine, diarrhea) used for matching, ranking (Indication Match), and evaluation. Domain Pack–governed.
- **Symptom Taxonomy**: Controlled taxonomy linking surface forms (AR/EN synonyms) to indication tags with many-to-many and hierarchical relationships; supports clarification prompts for ambiguous nodes.
- **Recommendation Candidate**: In-corpus product at a Product Identity level (brand/line/strength/package as applicable) with: matched indications; evidence pointers; safety outcome; ranking signal contributions; Recommendation Score (policy-composed).
- **Safety Label**: Extensible structured suitability/constraint record across Safety Model dimensions (pregnancy, breastfeeding, pediatric, elderly, renal/hepatic impairment, diabetes, hypertension, contraindications, interaction severity, OTC/prescription, …). v1 may populate a subset.
- **Recommendation Decision**: Outcome of recommend-mode for a query: recommend list / clarify / refuse / limited coverage; includes ordered candidates retained after Safety Filtering and Recommendation Ranking, plus policy-applied bounds.
- **Recommendation Trace**: Operator-facing attribution record (Quality Context / diagnostics aligned with 018): Need Frame summary, taxonomy mapping result, constraints, per-candidate matched indications, evidence pointers, safety outcomes, rank contributions, and decision type. Not a breaking public API resource.
- **Recommendation Policy**: Versioned Domain Pack (optional project override) rules for signal weights, recommendation count bounds, safety posture, clarification thresholds, language, identity presentation, and medical-advice separation.
- **Recommend Answer View**: User-facing ranked recommendations + evidence-backed rationale + caveats + citations (content of Answer under frozen `/answer` contract—not a new API resource).
- **Recommend Eval Case**: Golden item with need query, allow/forbid products (at stated identity level), safety expectations, clarification expectation, language, and graded relevance where needed for nDCG.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: Feature MUST respect Clean Architecture layer boundaries and Domain Pack extension patterns.
- **NFR-002**: I/O-bound operations MUST be async; public APIs MUST include type hints where code is added later.
- **NFR-003**: External providers (LLM, embedding, vector DB, reranker) MUST remain swappable via existing factory interfaces.
- **NFR-004**: Recommend-mode RAG answers MUST return source citations when retrieval is used.
- **NFR-005**: Project/system prompts and pack policies touched for recommendation MUST be versioned when modified.
- **NFR-006**: Unit and integration tests MUST cover intent detection, taxonomy mapping, filtering, ranking signal composition (where implemented), product identity handling, and corpus-boundedness behaviors.
- **NFR-007**: Structured logging MUST include correlation ids at service boundaries; recommend-mode markers MUST be attributable in traces.
- **NFR-008**: Secrets MUST NOT be stored in source control.
- **NFR-009**: Recommendation MUST remain a Domain Pack capability extension under 016 sole-owner rules and ADR-020-001 (Answer + Retrieval), not a second pipeline, service, or API.
- **NFR-010**: Clinical safety posture is conservative: prefer refuse/clarify over unsupported recommendation.
- **NFR-011**: Ranking and traces MUST be reviewable/explainable for operators without violating end-user Explanation Policy.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixed pharmacy recommendation golden set (≥20 need-based queries covering ≥5 indication buckets present in corpus), Corpus-Boundedness ≥90% (recommended options are only in-corpus products); False Recommendation Rate for out-of-corpus/fabricated products is within the 019 profile gate.
- **SC-002**: On Safety Model–constrained golden cases (v1: at least pregnancy/breastfeeding; additional dimensions when enabled), Safety Precision and Safety Recall meet the 019 profile gates, and ≥95% of runs apply the expected exclude/demote behavior for avoid/contraindicated labeled products (no silent first-line promotion of those products).
- **SC-003**: For high-confidence mapped needs with adequate corpus coverage, Recall@K / Precision@K / MRR (and nDCG when graded labels exist) meet the 019 recommendation profile gates, including ≥85% of cases with at least one indication-appropriate candidate in the top recommended set (golden allow-list).
- **SC-004**: Ambiguous-need cases produce clarification or explicit limited-coverage messaging in ≥90% of designated ambiguous golden items (Clarification Rate gate); not a long unrelated list.
- **SC-005**: Recommend-mode answers include citations for recommended claims in ≥95% of retrieval-backed golden cases.
- **SC-006**: Arabic need queries receive Arabic answers (and English→English) in ≥95% of bilingual smoke cases, consistent with existing language policy.
- **SC-007**: Architecture review confirms ADR-020-001: no Recommendation Service, no Recommendation API, no parallel production path, no new sole owner; 016/018 checklists pass for this feature’s design artifacts; frozen `/answer` contract unchanged (015).
- **SC-008**: A documented 019 recommendation eval profile exists and can be run offline against the golden set with the Evaluation Metrics catalog (as profiled) and defect attribution distinguishing taxonomy/retrieval misses vs ranking vs generation vs safety-filter errors.
- **SC-009**: On operator-trace golden samples, ≥95% of retained/excluded candidates expose Matched Indications, Safety Outcome, and Rank Contribution signals in Recommendation Trace / quality context (Candidate Explainability).
- **SC-010**: On product-family golden cases, recommendation lists respect Product Identity Rules (no package-only false duplicates occupying multiple slots when policy marks package irrelevant; distinct indication lines not incorrectly merged).

---

## Assumptions

- Initial scope is the **pharmacy** Domain Pack and projects using the pharmacy leaflet/corpus catalog (including the ~56-product enrichment set); other verticals are out of scope unless they reuse the same extension pattern later.
- Recommendation is **corpus-bounded decision support**, not a licensed clinical prescribing system; answers always allow “consult a pharmacist/physician” posture.
- Structured fields already evolving in corpus workbooks (pregnancy/breastfeeding enums, doses) are inputs to the Safety Model; **indication tags** and taxonomy coverage may start partially curated and improve iteratively.
- Leaflets remain the narrative evidence source until structured ingest fully carries tags; dual maintenance is acceptable during transition if index metadata stays consistent after reindex.
- External `/answer` contract stays frozen per 015/016; UI may later present ranked cards, but API stability rules still apply.
- Feature 019 hosts eval runners/profiles and metric implementation; this feature defines pharmacy recommendation requirements and the metric catalog those profiles must satisfy.
- Dose calculation, full OTC legal classification automation, and insurance formulary optimization are out of scope for v1 unless already represented as simple optional Formulary/Preference signals.
- Full multi-drug interaction graph reasoning is out of scope for v1; Interaction Severity MAY be used when simple concurrent-therapy signals are already available in evidence/labels.
- Logical Recommendation Flow steps may be thin wrappers over existing retrieval/answer behavior; thinness does not authorize a new pipeline.

---

## Principles (normative for later plan/tasks)

1. **Capability, not owner** — Recommendation extends pharmacy pack + sole Answer/Retrieval path (ADR-020-001).
2. **Corpus-bounded** — Never recommend products not in the project index.
3. **Taxonomy over vibes** — Candidate generation prefers Symptom Taxonomy + indication tags; generation only explains ranked evidence.
4. **Safety before cleverness** — Filters and refusals beat fluent unsafe answers.
5. **Clarify when unsure** — Low mapping confidence → clarification, not guesswork.
6. **Grounded claims** — Every recommended attribute must be evidence-backed (018); Explanation Policy forbids hidden-score storytelling.
7. **Reviewable ranking** — Recommendation Score signals are explicit; operators can inspect rank contribution.
8. **Identity-aware** — Brand/line/strength/package hierarchy guides ranking and presentation.
9. **Evaluable** — No recommend-mode ship without 019 profile coverage for critical buckets and metric catalog gates.
10. **M0 freeze** — No parallel production path, Recommendation Service, or Recommendation API without superseding exception ADR.

---

## Consistency Review *(specification self-check)*

| Check | Result |
|-------|--------|
| Scope unchanged (capability on sole Answer + Retrieval; pharmacy pack) | Pass |
| No Recommendation Service / API / new pipeline / new owner | Pass (ADR-020-001, FR-016, NFR-009, SC-007) |
| Frozen `/answer` contract (015) | Pass (FR-011, Non-goals) |
| 016 M0 freeze | Pass |
| 018 grounding / trace | Pass (Explanation Policy, FR-014, Candidate Explainability) |
| 019 owns metric implementation | Pass (Evaluation Metrics section, FR-013, SC-008) |
| User stories support new requirements | Pass (US1–need/rank; US2–safety model; US3–taxonomy ambiguity; US4–explanation policy; US5–metric catalog; US6–explainability) |
| Success criteria measurable | Pass (SC-001…SC-010) |
| No fixed ranking weights in spec | Pass (Policy-owned) |
| Logical flow ≠ new pipeline | Pass (explicit normative clarifications) |

---

## Milestones (specification-level; planning detail deferred)

| Milestone | Outcome |
|-----------|---------|
| **M0** | Spec + ADR-020-001 + architecture-review alignment (016/018); exception ADR only if ownership model changes |
| **M1** | Indication tag vocabulary + Symptom Taxonomy + product tag/identity coverage for priority buckets (acidity, pain/migraine, diarrhea, etc.) |
| **M2** | Recommend intent + expanded Need Frame in query understanding; clarify behavior |
| **M3** | Logical flow on sole path: constraints → retrieval/fusion/rerank → safety filter → recommendation ranking signals; Product Identity Rules |
| **M4** | Recommend-mode answer + Explanation Policy + Recommendation Policy (bounds, citations, language) |
| **M5** | 019 golden set + offline profile + metric catalog gates; Recommendation Trace / operator explainability |

Implementation sequencing, contracts, and tasks are intentionally **out of scope for this spec** and belong in `/speckit-plan` and `/speckit-tasks`.

# Contract: Ranking and Recommendation Policy

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22

---

## Recommendation Ranking Model

### Signals (normative names)

| Signal | Required when available |
|--------|-------------------------|
| Indication Match | Yes for tag-backed candidates |
| Retrieval Evidence | Yes when retrieval returned evidence |
| Reranker Confidence | When reranker applied |
| Safety Fitness | After Safety Filtering |
| Formulary / Preference | Optional; omit if unset |

### Composition rules

1. Recommendation Score MUST be a composition of the named signals above (pack MAY add signals only via versioned policy + architecture review).
2. **Weights and enablement are NOT fixed** in this contract; RecommendationPolicy owns them.
3. Ranking MUST be **reviewable**: operator Trace exposes rank contribution / signal breakdown.
4. Ranking MUST be **explainable** without requiring end-user disclosure of hidden numeric weights.
5. Ranking MUST NOT rely solely on an opaque score with no inspectable breakdown for operators.
6. Product Identity Rules MUST influence slotting (no false duplicate / false independent SKUs).

## Recommendation Policy (rule categories)

Policy MUST define (values versioned in pack; numbers not fixed here unless platform-wide elsewhere):

| Category | Normative intent |
|----------|------------------|
| Maximum recommendations | Cap user-facing list |
| Minimum recommendations | Optional floor when coverage adequate |
| Prefer higher evidence | Evidence-stronger peers win ties appropriately |
| Prefer safer candidate | Under population constraints, safer ranks higher |
| Never out-of-corpus | Hard fail if violated |
| Always provide citations | For retrieval-backed recommend claims |
| Clarify instead of guessing | Low confidence / ambiguity |
| Respect language policy | AR↔AR, EN↔EN |
| Respect product identity | Present at correct identity level |
| Separate recommendation from medical advice | Caveat posture |
| Signal weights | Score composition |

## Explanation Policy (answer content)

1. Explain using **retrieved evidence only**.
2. MUST NOT explain using hidden scores or unaudited weight stories.
3. MUST NOT fabricate reasons or claim clinical superiority without evidence.
4. MUST distinguish corpus-bounded recommendation from medical advice / prescribing.
5. User-facing text MAY use qualitative fit language; MUST NOT dump internal rank tables to end users.

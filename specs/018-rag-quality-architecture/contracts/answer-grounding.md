# Contract: Answer Grounding & Verification

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative contracts for claim-level grounding, logical verification, citation resolution, conflict disclosure, and no-answer decisions — all under Answer Generation ownership.

---

## Purpose

Maximize final answer quality and prevent hallucinations without creating a second answer pipeline.

---

## A. Logical Verification Responsibilities

Inside Canonical Answer Generation Owner only:

```text
Answer Draft
    → Claim Extraction
    → Evidence Verification
    → Citation Resolution
    → Final Answer
```

### Rules

1. These are logical responsibilities, **not** a separate production owner or path (C8).
2. Verification operates only on Context + draft; no re-retrieve, re-plan, or second context assembly.
3. Prompt instructions affecting grounding/disclosure MUST be versioned when changed.

---

## B. Claim-Level Grounding (C12)

1. Grounding applies per claim, not only per whole answer.
2. A claim without supporting **included** evidence MUST NEVER be marked or presented as grounded.
3. Unsupported claims MUST be removed, limited, or explicitly flagged — never silently left as grounded facts.
4. Whole-answer “looks fine” is insufficient if any claim lacks support.

---

## C. Citation Resolution (C5)

1. Resolved citations MUST come only from Context citation map.
2. Citation chain Evidence → Chunk → Document → Source → Citation MUST hold for cited material.
3. Unknown/fabricated citation markers are continuity failures (omit + flag / fail closed per Answer policy — never invent sources).

---

## D. Conflict Disclosure (C4)

1. When Context carries surviving conflicts, Answer MUST disclose disagreement.
2. Silent side-picking is forbidden.
3. Budget omission upstream is not agreement.

---

## E. No-Answer Decision Model

Answer Generation decides using upstream signals. Architectural conditions:

| Condition | Expectation |
|-----------|-------------|
| No evidence | Explicit no-answer; no generative fill-in |
| Weak evidence | Limited or no-answer; no overconfidence |
| Conflicting evidence | Disclose; may refuse single definitive answer |
| Partial evidence | Answer supported facets only; state gaps |
| Ambiguous query | Clarification or non-definitive posture |
| Out-of-domain | Unsupported / out-of-scope posture |
| Restricted answer | Refuse/constrain per policy; no fabrication |

Upstream stages own signal honesty; Answer owns the user-visible decision.

---

## Acceptance

Designs that allow ungrounded claims as grounded, invent citations, hide conflicts, or fill empty evidence with parametric knowledge fail review.

---

## Non-Goals

- LLM provider selection
- Exact disclosure wording (Domain Packs may supply profiles)
- Redefining Feature 014 faithfulness metrics

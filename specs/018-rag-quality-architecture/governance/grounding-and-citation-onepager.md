# Grounding & Citation One-Pager (018)

## Claim-level grounding (C12)

- Grounding applies **per claim**, not only per whole answer.
- A claim without supporting **included** evidence MUST NEVER be marked or presented as grounded.
- Unsupported claims are removed, limited, or flagged — never silently left as grounded facts.

## Citation chain (C5)

```text
Evidence → Chunk → Document → Source → Citation
```

- Every included Context block needs a complete chain entry.
- Compression/budgeting must preserve the chain for retained blocks.
- Answer citations resolve only from the Context citation map — never invent sources.

## Logical verification (Answer Generation only)

```text
Draft → Claim Extraction → Evidence Verification → Citation Resolution → Final Answer
```

Not a separate production owner or parallel pipeline (C8).

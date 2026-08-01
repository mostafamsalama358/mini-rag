# Quality Architecture Review Checklist (018)

**Purpose**: Accept/reject answer & retrieval quality contract changes without creating parallel paths or new owners.  
**References**: Contracts C1–C12, [`../contracts/compatibility.md`](../contracts/compatibility.md), [`../governance/modularity-freeze.md`](../governance/modularity-freeze.md), Feature 016 M0.

## MUST

- [ ] Change extends a canonical stage owner (016) — does not invent a Quality / Coverage / Verification pipeline owner
- [ ] No new parallel retrieval path
- [ ] No new parallel answer path (015 dual-run remains transitional only)
- [ ] Coverage validation remains Evidence-owned; Answer Generation is not sole coverage authority
- [ ] Feature 014 evaluation remains offline — not a request-path production owner
- [ ] Planner does not re-parse as competing Understood Query authority (C9)
- [ ] Citation continuity Evidence→Chunk→Document→Source→Citation preserved for included/cited material (C5)
- [ ] Claim-level grounding: unsupported claims cannot be marked grounded (C12)
- [ ] Filters cannot be silently dropped (C2)
- [ ] Conflicts: omission ≠ agreement; survivors disclosed (C4)
- [ ] Quality Context enrichments are additive/namespaced; no upstream overwrite (C11)
- [ ] Extensions are tighten-only relative to C2/C5/C7/C8/C9/C10/C12
- [ ] Compatibility with 014/015/016/017 checked ([`relationship-to-014-017.md`](../governance/relationship-to-014-017.md))
- [ ] No algorithms/provider winners/package paths presented as architecture ownership truth

## MUST REJECT

- [ ] Parallel quality-only retrieval stack
- [ ] Mega-stage merge of Planner+Engine+Evidence as one production owner
- [ ] Answer-as-sole-coverage-owner designs
- [ ] 014-as-runtime-owner / inline judge ownership
- [ ] Silent strategy-family substitution without traced degradation
- [ ] Fabricated evidence/citations/parametric fill-in on empty context

## Notes

Reviewer: ________  Date: ________  Outcome: Accept / Reject / Accept-with-follow-up

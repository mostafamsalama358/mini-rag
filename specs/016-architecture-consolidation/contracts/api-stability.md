# Contract: External Answer API Stability (Consolidation Window)

**Feature**: 016-architecture-consolidation | **Version**: 1.0.0  
**Related**: `specs/015-unified-pipeline-migration/contracts/api-stability.md` (field-level detail)  
**Authority**: ADR-003

---

## Purpose

During architecture consolidation, the **external answer interaction contract** remains frozen so clients and operators are not coupled to internal ownership changes.

---

## Normative Rules

1. Internal concern ownership, contracts, and orchestration MAY change.
2. External request/response field names, optionality, success/error signals, and status semantics for the answer capability MUST NOT change under 016 alone.
3. Only the Application concern **external response adaptation** may translate internal results to the external contract.
4. Presentation MUST NOT embed core algorithms to “make up for” adaptation gaps.
5. A separate API-redesign specification is required to intentionally break or version this contract (016 Out of Scope).

---

## Compatibility Window

| Phase | External contract |
|-------|-------------------|
| M0–M7 | Frozen |
| After consolidation | Remains frozen until a dedicated API change spec |

---

## Search and Other APIs

- Search external contract is **not** redesigned here.
- Search MAY retain an explicit interim retrieval owner (ADR-002) but MUST NOT silently change ranking semantics without a validation gate.
- Other endpoints are out of scope unless they become hidden answer paths (forbidden).

---

## Non-Goals

- Listing every response field (see 015 api-stability for current field-level freeze)
- Redesigning prompts, citations payload, or auth
- Performance SLOs

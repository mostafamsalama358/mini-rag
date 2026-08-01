# Contract: Query Understanding Handoff

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative handoff from Query Understanding to Retrieval Planner.

---

## Purpose

Ensure Planner consumes a canonical Understood Query and never becomes a second parse authority.

---

## Producer / Consumer

| Role | Party |
|------|-------|
| Producer | Canonical Query Understanding Owner |
| Primary consumer | Canonical Retrieval Plan Owner |
| Other consumers | Application (Answer) for clarification UX; Quality Context enrichment |

---

## Required Signals

Understood Query MUST include:

- Parsed intent
- Ambiguity
- Confidence
- Extracted entities (grounded)
- Extracted constraints
- Clarification requirement
- Degradation reason (when applicable)

See [data-model.md](../data-model.md) `UnderstoodQuery`.

---

## Rules

1. Planner MUST treat Understood Query as authoritative for intent, entities, and constraints.
2. Planner MUST NOT re-parse raw user text to invent a conflicting intent (Contract C9).
3. When `clarification_required=true`, Planner MUST propagate non-certainty (clarification/degraded plan) rather than a high-confidence unconstrained strategy set.
4. Fabricated entities/fields in Understood Query are forbidden; failures MUST surface as clarification or degradation.
5. Domain Packs may inject vocabulary/profiles into Query Understanding; they MUST NOT own the handoff contract.

---

## Acceptance

Architecture review fails if a design allows Planner (or Engine) to silently ignore clarification/ambiguity signals or re-parse as a competing authority.

---

## Non-Goals

- Specifying parser models or prompting
- Defining clarification UI copy
- Changing frozen external answer API fields

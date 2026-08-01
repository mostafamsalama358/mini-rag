# Contract: Retrieval Quality (Strategy & Candidate Lifecycle)

**Feature**: 018-rag-quality-architecture | **Version**: 1.0.0

Normative contracts for Planner strategy architecture and Engine candidate lifecycle (including score calibration).

---

## Purpose

Maximize retrieval quality while preserving the plan/execute boundary.

---

## A. Strategy Architecture (Planner-owned)

### Required concepts

- Strategy Registry
- Strategy Capability Model
- Strategy Selection policy
- Strategy Ordering policy
- Strategy Degradation policy
- Strategy Compatibility rules

### Rules

1. Every selected strategy MUST exist in the registry and carry a non-empty justification tied to Understood Query signals and capabilities.
2. Strategy order MUST be deterministic for identical Understood Query + configuration.
3. Degradation MUST be explicit (narrowed set, clarification, conservative constraints + reason).
4. Incompatible combinations MUST NOT be co-selected without compatibility rationale.
5. Meta-strategies MUST expand only into registered component strategies.
6. Planner MUST NOT execute retrieval, expand against indexes, rerank, calibrate scores, or assemble evidence.

### Acceptance

A plan without per-strategy justification, or with silent unconstrained strategy invention under ambiguity, fails review.

---

## B. Candidate Lifecycle (Engine-owned)

Logical order and ownership (all Engine unless noted):

1. Candidate Retrieval  
2. Candidate Normalization  
3. Filter Pushdown  
4. Query Expansion  
5. Fusion  
6. Identity Deduplication  
7. Reranking  
8. Score Calibration  
9. Candidate Selection → RetrievalResult handoff to Evidence  

### Rules

1. Engine MUST honor plan strategy order/constraints (Contract C1).
2. Filters MUST be applied pushdown or residual before Evidence Pack formation, or listed unapplied with reason (C2).
3. Expansion MUST stay within plan-allowed policy; variants attributed in Expansion Trace.
4. Reranking is distinct and disable-safe; disablement traced in Rerank Trace.
5. Score calibration MUST normalize heterogeneous signals (dense, sparse, metadata quality, reranker output, etc.) before Candidate Selection, with provenance — **no mathematics prescribed**.
6. Candidate Selection MUST budget/cap before Evidence receives results.
7. Engine MUST NOT re-plan intent, organize Evidence Packs, assemble LLM context, or generate answers.
8. Evidence MUST NOT re-run primary candidate retrieval.

### Acceptance

Designs that relocate calibration to Evidence/Answer as a competing authority, or allow silent filter loss, fail review.

---

## Non-Goals

- Choosing reranker/embedding providers
- Defining fusion/calibration formulas
- Store-specific query syntax

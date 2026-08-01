# ADR-020-001 — Recommendation as Capability (not Service / API / Parallel Path)

**Feature**: `020-pharmacy-recommendation`  
**Status**: Accepted  
**Date**: 2026-07-22  
**Related**: Features 015 (frozen `/answer`), 016 (sole-owner / M0 freeze), 018 (quality/trace), 019 (evaluation ownership)

## Context

Pharmacy users need need-based product recommendations (“دواء للحموضة؟”). Alternatives considered included a dedicated Recommendation Service, a dedicated Recommendation API, or a parallel recommend pipeline. Those options would create a new production owner, risk breaking the frozen external answer contract, and violate M0 freeze / 016 sole-path rules.

## Decision

1. **Recommendation remains a Capability** of the pharmacy Domain Pack, exercised through the **existing Retrieval + Answer architecture**.
2. **No Recommendation Service** as a standalone production microservice or new sole owner module.
3. **No Recommendation API** as a dedicated public resource; user-visible output remains **answer content** under the frozen external `/answer` contract (015 / 016 ADR-003).
4. **No parallel production path** for recommendation (016 M0 freeze).
5. **Ownership stays**:
   - Need Frame / recommend intent → existing Query Understanding concern
   - Candidate constraints, hybrid retrieval, fusion, rerank, ranking signals → existing Retrieval owners
   - Safety filtering + Recommendation Score composition → policy-governed behavior on the sole path (not a new owner)
   - Final recommend answer + explanation → existing Answer owner
6. Logical Recommendation Flow in the feature spec is a **concern ordering for review**, not a new deployable pipeline.

## Alternatives considered

| Option | Why rejected |
|--------|----------------|
| (A) Dedicated Recommendation Service + API | New sole owner; parallel path; API surface expansion; M0 freeze violation |
| (B) Parallel recommend pipeline dual-run with answer | Second production path; cutover/ownership confusion; 016 violation |
| (C) Capability on sole Answer + Retrieval path (**selected**) | Preserves frozen contract, ownership registry, and quality/eval alignment |

## Tradeoffs

- Ranking and safety logic must be expressed as **pack policy + extensions** of existing stages rather than an isolated service—slightly less isolation, much stronger governance fit.
- Operator explainability uses Quality Context / Recommendation Trace (018-aligned), not a new public recommend API.
- Metric implementation remains under **019**; this feature only defines the recommend metric catalog and requirements.

## Scope

- In: pharmacy Domain Pack recommend-mode capability design and ADR binding for 020.
- Out: implementation, numeric ranking weights, new HTTP routes, exception to create a Recommendation owner.

## Duration

Standing decision for Feature 020 unless superseded.

## Exit criteria / supersession

A dedicated Recommendation owner, service, or API requires a **superseding exception ADR under 016** with explicit scope, duration, and exit criteria. Until then, ADR-020-001 remains binding.

## Traceability

| Spec anchor | Binding |
|-------------|---------|
| FR-016, NFR-009, SC-007 | Normative requirements |
| Principles 1 & 10 | Capability + M0 freeze |
| Logical Recommendation Flow | Explicitly not a new pipeline |

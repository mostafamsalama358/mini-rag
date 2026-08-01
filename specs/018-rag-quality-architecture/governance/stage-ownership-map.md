# Stage Ownership Map (018)

Primary owner per quality concern. Logical parties only — never folder paths.  
Aligned with 016 ownership; 018 extends contracts, does not reassign owners.

| Concern | Primary Owner | Secondary Safety-Net | Spec Section | Contract IDs |
|---------|---------------|----------------------|--------------|--------------|
| Understood Query production | Query Understanding | — | §1 | C9 |
| Understood Query → Planner handoff | Query Understanding | Retrieval Plan (consumer) | §1 | C9 |
| Planner robustness / no re-parse | Retrieval Plan | — | §1–2 | C9 |
| Strategy Registry | Retrieval Plan | Domain Packs (hints) | §2 | C1 |
| Strategy Capability Model | Retrieval Plan | — | §2 | C1 |
| Strategy Selection policy | Retrieval Plan | — | §2 | C1 |
| Strategy Ordering policy | Retrieval Plan | — | §2 | C1 |
| Strategy Degradation policy | Retrieval Plan | — | §2 | C1 |
| Strategy Compatibility rules | Retrieval Plan | — | §2 | C1 |
| Candidate Retrieval | Retrieval | — | §3 | C1 |
| Candidate Normalization | Retrieval | — | §3 | C1 |
| Filter Pushdown | Retrieval | Retrieval Plan (declares filters) | §3 | C2 |
| Query Expansion | Retrieval | — | §3 | C1 |
| Fusion | Retrieval | — | §3 | C3 |
| Identity Deduplication | Retrieval | Evidence (content dedup) | §3 | C3 |
| Reranking | Retrieval | — | §3 | C1 |
| Score Calibration | Retrieval | — | §4 | C1 |
| Candidate Selection | Retrieval | — | §3 | C6 |
| Evidence Quality Model | Evidence | — | §5 | C10 |
| Coverage Validation | Evidence | Context (budget impact note) | §6 | C10 |
| Missing Evidence Detection | Evidence | Answer Generation (consumes) | §7 | C10 |
| Evidence Ordering | Evidence | — | §5 | C3 |
| Content Deduplication | Evidence | Context (final safety-net) | §3/C3 | C3 |
| Conflict Candidates / Categories | Evidence | Context (disclosure-ready) | §11 | C4 |
| Context Priority Model | Context | — | §8 | C6 |
| Context Compression Policy | Context | — | §9 | C5,C6,C12 |
| Citation Map / Chain assembly | Context | Answer Generation (resolution) | §10 | C5 |
| Conflict Groups / budget omission | Context | Answer Generation (disclosure) | §11 | C4 |
| Final Dedup Safety-Net | Context | — | C3 | C3 |
| Answer Draft | Answer Generation | — | §12 | C7 |
| Claim Extraction | Answer Generation | — | §12 | C12 |
| Evidence Verification | Answer Generation | — | §12 | C12 |
| Citation Resolution | Answer Generation | — | §12 | C5 |
| Final Answer | Answer Generation | Application (external adapt) | §12 | C7 |
| Claim-Level Grounding | Answer Generation | — | §13 | C12 |
| No-Answer Decision | Answer Generation | Upstream signal providers | §15 | C7,C10 |
| Hallucination Prevention (terminal enforcement) | Answer Generation | Upstream stages contribute signals | §14 | C7 |
| Quality Context continuity contract | Composition | Stage enrichers (namespaced) | §20 | C11 |
| Quality Trace continuity contract | Composition | Offline Evaluation (consumes) | §16 | C11 |
| Stage Quality Metrics catalog authority | Offline Evaluation | Stage diagnostics feed offline | §17 | C10 |
| Offline Feedback Loop | Offline Evaluation | Composition (wiring config) | §18 | C8 |
| Extension Points wiring | Composition | Domain Packs / providers | §19 | C8 |
| Modularity Freeze | Composition | — | C8 | C8 |

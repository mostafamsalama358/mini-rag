# Extension Points Registry (018)

From spec §19 and [`../contracts/quality-observability.md`](../contracts/quality-observability.md).

**Tighten-only rule**: Extensions MAY tighten quality (more conservative no-answer, stricter filters, richer disclosure). They MUST NOT weaken C2, C5, C7, C8, C9, C10, or C12, and MUST NOT capture core stage ownership. Composition remains sole wiring authority.

| Stage | Extension point | Example extension kind |
|-------|-----------------|------------------------|
| Query Understanding | Vocabulary / entity catalogs | Domain Pack profile |
| Query Understanding | Field profiles / clarification templates | Domain Pack profile |
| Retrieval Plan | Strategy registry hints | Domain Pack hint |
| Retrieval Plan | Constraint vocabularies / selection policy profiles | Policy profile |
| Retrieval | Retriever adapters | Provider adapter |
| Retrieval | Expansion adapters | Provider adapter |
| Retrieval | Reranker providers / store capability declarations | Provider adapter |
| Evidence | Evidence quality signal enrichers | Pack/utility under Evidence owner |
| Evidence | Conflict-candidate detectors | Under Evidence owner |
| Context | Compression adapters | Provider/utility adapter |
| Context | Priority profile packs / stitch ordering profiles | Policy profile |
| Answer Generation | Prompt capability modules | Domain Pack module |
| Answer Generation | Disclosure wording packs | Domain Pack profile |
| Answer Generation | Grounding policy profiles | Policy profile |

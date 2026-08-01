# Ownership Registry

**Feature**: 016-architecture-consolidation  
**Schema**: `OwnershipBinding` from [`../data-model.md`](../data-model.md)  
**Rule**: Exactly one Owner per production concern. Owners are **logical parties**, never folder paths.

| concern_id | description | production | owner | contributors | consumers | selection_rationale | selected_at_phase |
|------------|-------------|------------|-------|--------------|-----------|---------------------|-------------------|
| query_understanding | Parse/understand user query into canonical understood-query contract | yes | Canonical Query Understanding Owner | Domain Packs (injected profiles) | Retrieval Plan Owner; Application (Answer) | Architectural alignment + production maturity of shared parse concern | M1 |
| retrieval_planning | Produce retrieval plan intent from understood query | yes | Canonical Retrieval Plan Owner | Domain Packs (strategy hints via profiles) | Retrieval Execution Owner | Alignment with plan-stage boundary; extensibility via packs | M1 |
| retrieval_execution | Execute retrieval (dense/sparse/fusion/expand/rerank orchestration) | yes | Canonical Retrieval Owner | Infrastructure adapter authors | Evidence Owner; Search (post-cutover); Application (Answer) | Production maturity + operational stability + validation; not by novelty (AP12) | M2 |
| evidence_organization | Select/dedup/disclose evidence set | yes | Canonical Evidence Owner | Shared pure-utility contributors under Owner | Context Assembly Owner | Concern boundary clarity + maintainability | M1 |
| context_assembly | Assemble prompt context from evidence | yes | Canonical Context Owner | — | Answer Generation Owner | Single responsibility for assembled-context contract | M1 |
| answer_generation | Generate grounded answer + citation assembly | yes | Canonical Answer Generation Owner | — | Application (Answer adaptation) | Terminal generation concern; citations as contract property | M1 |
| external_answer_adaptation | Map internal answer to frozen external answer contract | yes | Application (Answer) | — | Presentation / clients | ADR-003 adaptation at Application edge | M1 |
| composition_wiring | Bind interfaces; select active production implementations | yes | Composition | Registration helpers (Application) | All runtime entrypoints | P6 Composition exclusivity | M0 |
| document_parsing | Parse authorized content to parsed-document contract | yes | Canonical Document Parse Owner | Format plugin authors under Owner registry | Chunking Owner; Application (Ingest) | Single format-registry authority | M4 |
| chunking_embed_text | Chunking + sole embed-text policy | yes | Canonical Chunking Owner | Domain Packs (injected profiles) | Persist & Index; retrieval data plane | One embed-text policy authority (P3/P4) | M4 |
| persist_index | Persist and index indexable units | yes | Application (Ingest) + Infrastructure (providers) | — | Retrieval data plane | Application orchestrates; Infrastructure implements persistence | M4 |
| ingest_orchestration | Ingest use-case orchestration | yes | Application (Ingest) | Composition; async workers | Presentation; operators | Application owns use-case facade | M4 |
| search_response_adaptation | Map retrieval results to external search response | yes | Application (Search) | — | Presentation / clients | Application adaptation pattern (parallel to answer) | M2-interim |
| search_query_intake | Search query intake as needed | yes | Application (Search) | — | Retrieval Execution Owner | Thin intake; no second retrieval owner | M2-interim |
| domain_vocabulary | Domain vocabulary and vertical heuristics | yes | Domain Packs | Vertical authors | Query Understanding; Retrieval Plan; Chunking (via injection) | P8/P12 — packs extend without capturing core | M6 |
| provider_implementations | LLM/embedding/vector/rerank/persistence providers | yes | Infrastructure | — | Composition (wiring); Core via interfaces only | P7 Infrastructure behind interfaces | M0 |
| offline_evaluation_orchestration | Offline eval orchestration | yes (offline only) | Offline Evaluation Owner | Metric contributors | Release/cutover process | I11 — not on request path | M1 |
| offline_scoring | Scoring for offline evaluation | yes (offline only) | Offline Evaluation Owner | Metric contributors | Offline Evaluation Owner | Same owner as evaluation capability | M1 |
| offline_reporting | Evaluation reporting | yes (offline only) | Offline Evaluation Owner | — | Release/cutover process | Offline-only consumer set | M1 |
| structured_knowledge | Structured knowledge extraction/representation | no | Platform Architecture (process) | Knowledge capability maintainers | None until activation | ADR-004 Activation Pending Consumer | M8 |

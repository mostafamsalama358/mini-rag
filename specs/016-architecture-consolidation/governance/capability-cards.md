# Capability Cards

**Feature**: 016-architecture-consolidation  
**Source**: [`../spec.md`](../spec.md) Canonical Architecture  
**Note**: Orchestration order is not identity (P14). Required concerns + contracts + ownership define the capability.

---

## Answer

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Turn an authorized user question into a grounded answer under the frozen external contract |
| **Required Concerns** | `query_understanding`; `retrieval_planning`; `retrieval_execution`; `evidence_organization`; `context_assembly`; `answer_generation`; `external_answer_adaptation`; `composition_wiring` |
| **Required Contracts** | `understood_query`; `retrieval_plan_intent`; `retrieval_results`; `evidence_set`; `assembled_context`; `generated_answer`; `external_answer_response` |
| **Ownership** | See [`ownership-registry.md`](./ownership-registry.md) — one Owner per concern; adaptation Application-owned; wiring Composition-owned |
| **Allowed Dependencies** | Presentation → Application/Composition; Application → Core interfaces + Domain Pack profiles; Core → peer contracts + injected profiles; Composition → wiring only; Core → Infrastructure interfaces only |
| **Forbidden Dependencies** | Core → concrete infrastructure; Infrastructure → orchestration; Domain Packs → core control flow; Presentation → core algorithms; second production Answer path |

---

## Ingest

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Turn authorized content into durable, retrievable indexed knowledge units |
| **Required Concerns** | `document_parsing`; `chunking_embed_text`; `persist_index`; `ingest_orchestration`; `composition_wiring` |
| **Required Contracts** | `parsed_document`; `indexable_units`; `persistence_ack` |
| **Ownership** | Parse, chunking, ingest orchestration each one Owner; Infrastructure owns provider persistence implementations |
| **Allowed Dependencies** | Application ingest → parse/chunk interfaces → infrastructure persistence interfaces; Domain Packs may inject parse/chunk profiles |
| **Forbidden Dependencies** | Multiple production chunking entrypoints; infrastructure-owned chunk policy; domain packs owning ingest control flow; `structured_knowledge` on path unless Active Production |

**Optional concern**: `structured_knowledge` — only when lifecycle is Active Production with declared consumer (ADR-004).

---

## Search

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Return ranked retrievable units for an authorized query without answer generation |
| **Required Concerns** | `search_query_intake`; `retrieval_execution`; `search_response_adaptation`; `composition_wiring` |
| **Required Contracts** | `retrieval_results` (reuse); `external_search_response` |
| **Ownership** | After consolidation: same `retrieval_execution` Owner as Answer. Until then: explicit interim Owner in [`search-interim-ownership.md`](./search-interim-ownership.md) |
| **Allowed Dependencies** | Presentation → Application → retrieval interfaces; Composition wiring |
| **Forbidden Dependencies** | Undocumented retrieval stack divergent from stated owner; silent semantic change without validation gate |

---

## Offline Evaluation

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Measure answer/retrieval quality offline for release and cutover decisions |
| **Required Concerns** | `offline_evaluation_orchestration`; `offline_scoring`; `offline_reporting` |
| **Required Contracts** | `evaluation_suite_io` (distinct from runtime answer contracts) |
| **Ownership** | Offline Evaluation Owner for all three concerns |
| **Allowed Dependencies** | May invoke production concerns in non-production environments through published interfaces |
| **Forbidden Dependencies** | Presence on production request path (I11); replacing architecture decisions with metric gaming |

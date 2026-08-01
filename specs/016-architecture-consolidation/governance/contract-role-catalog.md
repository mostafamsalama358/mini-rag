# Contract Role Catalog

**Feature**: 016-architecture-consolidation  
**Rule**: One canonical ContractRole per shared concept in production (P3). Names are concept roles, not concrete type names.

| role | concept | owner_concern | compatibility_policy |
|------|---------|---------------|----------------------|
| understood_query | Understood user query | query_understanding | Breaking change requires Owner approval + consumer notice |
| retrieval_plan_intent | Retrieval plan intent | retrieval_planning | Breaking change requires ADR if multi-capability impact |
| retrieval_results | Retrieval results | retrieval_execution | Shared by Answer and Search; one family only |
| evidence_set | Evidence set | evidence_organization | Citation lineage signals belong here or documented cross-cut |
| assembled_context | Assembled context | context_assembly | Consumed by answer_generation only as peer contract |
| generated_answer | Generated answer | answer_generation | Adapted externally by Application — not forked |
| external_answer_response | External answer API response | external_answer_adaptation | Frozen during consolidation (ADR-003) |
| parsed_document | Parsed document | document_parsing | Single parse contract for ingest |
| indexable_units | Chunk set / indexable units | chunking_embed_text | Embed-text policy is part of this authority |
| persistence_ack | Persistence acknowledgment | persist_index | Infrastructure implements; Application orchestrates |
| external_search_response | External search response | search_response_adaptation | Not redesigned by 016; no silent ranking change |
| evaluation_suite_io | Offline evaluation input/output | offline_evaluation_orchestration | Distinct from runtime answer contracts |

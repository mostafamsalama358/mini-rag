# Lifecycle Registry

**Feature**: 016-architecture-consolidation  
**Vocabulary**: [`../contracts/lifecycle.md`](../contracts/lifecycle.md)

| subject_id | kind | lifecycle_state | notes | exit_or_next |
|------------|------|-----------------|-------|--------------|
| answer_production_path | capability_path | active_production_owner | Target: single user-visible Answer path (ADR-001); cutover via 015 | Maintain sole owner after M1 |
| answer_parallel_stacks | competitor | retire_after_cutover | Competing Answer implementations after sole-owner soak | M7 retirement gate |
| retrieval_execution | concern | active_production_owner | Canonical Retrieval Owner after M2 | — |
| retrieval_execution_competitors | competitor | retire_after_cutover / consolidate_into_owner | Competing retrieval stacks | Owner Selection + M2/M7 |
| chunking_embed_text | concern | active_production_owner | Sole chunking + embed-text policy after M4 | — |
| chunking_alternate_entrypoints | competitor | retire_after_cutover | Alternate production chunking entrypoints | M4 then M7 |
| dual_run_shadow_diagnostics | tooling | transitional_diagnostic | Never user-visible owner (I10) | Retire After Cutover after M1 sole-path (M7) |
| search_retrieval_ownership | concern | active_production_owner (interim) | Interim owner explicit until shares Answer retrieval owner (ADR-002) | See `search-interim-ownership.md` |
| structured_knowledge | capability | activation_pending_consumer | ADR-004 — not production-complete | Activate only with declared consumer + Owner Selection |
| graph_retrieval_without_backing | capability | research_capability | Must not pretend to be production retrieval | Archive with knowledge decision or implement backing |
| offline_evaluation | capability | active_production_owner | Offline gate only; not request-path | — |
| duplicate_contracts | contract_debt | consolidate_into_owner | One ContractRole per concept after M3 | M3 gate |
| domain_heuristics_in_core | debt | consolidate_into_owner | Consolidate into Domain Packs (M6) | `domain-leakage-inventory.md` |
| dead_unreachable_alternates | debt | retire_after_cutover | No feature replacement implied | M7 |

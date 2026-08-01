# Domain Leakage Inventory

**Disposition target**: Consolidate Into Domain Packs (M6)  
**Owner of domain vocabulary**: Domain Packs

Findings are **concern-level**, not package-winner prescriptions.

| id | concern_affected | symptom (logical) | disposition | status |
|----|------------------|-------------------|-------------|--------|
| DL-001 | domain_vocabulary / query_understanding | Vertical keyword/heuristic defaults living in core parse path | Consolidate Into Domain Packs | open |
| DL-002 | domain_vocabulary / retrieval_planning | Domain-specific plan branches in shared planning | Consolidate Into Domain Packs | open |
| DL-003 | domain_vocabulary / answer path | Vertical field branches in application answer orchestration | Consolidate Into Domain Packs or pack-driven strategy hooks | open |
| DL-004 | domain_vocabulary / structured_knowledge | Vertical measurement/entity patterns in knowledge extractors while knowledge is non-production | Keep out of Active Production; if activated, pack-inject patterns | deferred (ADR-004) |

## Process

1. Add rows when leakage is discovered.
2. Do not “fix” by renaming folders — change ownership of the heuristic to Domain Packs.
3. Close rows only when ownership registry + packs reflect the move and M6 checklist passes.

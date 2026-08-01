# Domain Pack Extension Guide

**Feature**: 016-architecture-consolidation  
**Principles**: P8, P12

## Goal

Extend vertical behavior through **Domain Packs** without becoming a second owner of core orchestration.

## Allowed

- Add/change pack vocabulary, heuristics, and profiles consumed via injection
- Contribute under Canonical Owners as **Contributor** when pack profiles require Owner approval
- Reuse canonical ContractRoles from [`contract-role-catalog.md`](./contract-role-catalog.md)

## Forbidden

- Editing core orchestration control flow to hardcode a vertical
- Composition owning domain heuristics (AP5)
- Claiming a new parallel production path for domain-specific retrieval/answer stacks (AP1)

## Checklist for a new pack

1. Identify concerns that will consume pack profiles (usually query understanding, planning, chunking).
2. Confirm those concerns’ Owners remain unchanged in [`ownership-registry.md`](./ownership-registry.md).
3. Ensure Domain Packs remain Owner of `domain_vocabulary`.
4. Run architecture-review checklist for capability impact.
5. No core OwnershipBinding rows should gain the new vertical as Owner.

## Related

- Field registry / packs: platform field-pack model (spec 002)
- Leakage inventory: [`domain-leakage-inventory.md`](./domain-leakage-inventory.md)
- M6 gate: [`../checklists/m6-domain-extraction.md`](../checklists/m6-domain-extraction.md)

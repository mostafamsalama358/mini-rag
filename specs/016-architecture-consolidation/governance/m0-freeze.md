# M0 — Dual-Path Growth Freeze

**Phase**: M0  
**Status**: Active  
**Date**: 2026-07-18

## Rule

No new features may deepen **parallel production implementations** for the same concern without an approved ADR that explicitly supersedes P2/P4/AP1 for a bounded scope and duration.

## Allowed

- Work that moves consumers toward a single Active Production Owner
- Transitional diagnostics (dual-run/shadow) that never become the user-visible response owner (I10)
- Documentation, registries, and validation under 016
- Answer cutover work via the 015 vehicle toward sole-path

## Forbidden

- New selectable production stacks alongside an existing production owner for the same concern
- Treating feature flags as permanent architecture (AP8)
- Undocumented divergent Search/Answer retrieval ownership (I13)

## References

- [`../spec.md`](../spec.md) Migration Order M0, Principles P2/P4, Anti-Patterns AP1/AP8/AP9/AP10
- [`relationship-to-015.md`](./relationship-to-015.md)

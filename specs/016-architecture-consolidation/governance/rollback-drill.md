# Rollback Drill (Pre-M7)

**Feature**: 016-architecture-consolidation  
**Required before**: M7 retirement wave

## Purpose

Prove that path selection / prior release can restore the previous sole path before retiring competitors.

## Procedure

1. Record current production path/owner identity (Composition selection / release tag).
2. In a non-production or approved window, switch to the prior path selection (015 mode flip or prior release per Compatibility Strategy).
3. Verify next requests are served by the restored owner (observability / logs).
4. Verify external answer contract unchanged (`contracts/api-stability.md`).
5. Restore intended sole-path configuration.
6. Attach evidence (timestamp, operator, outcome) to the retirement gate checklist.

## After M7

Rollback is **prior release redeploy**, not in-place resurrection of retired paths.

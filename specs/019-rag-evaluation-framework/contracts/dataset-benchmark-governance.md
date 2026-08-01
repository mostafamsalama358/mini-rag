# Contract: Dataset & Benchmark Governance

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative governance for evaluation datasets and benchmarks.

---

## Purpose

Make release and regression claims reproducible, auditable, and change-controlled.

---

## Shared lifecycle

Draft → In Review → Approved → Frozen → Retired / Superseded

| Phase | Rule |
|-------|------|
| Draft | Editable; not eligible for blocking gates |
| In Review | Change-controlled proposal |
| Approved | Eligible for designated non-blocking or preparatory use |
| Frozen | Immutable content identity for a version; required for PR/Release pins |
| Retired | Not for new blocking runs; retained historically |
| Superseded | Replaced by newer freeze; readable for diffs |

---

## Dataset rules

1. **Approval** — Blocking tiers require explicit approval before freeze (who/what/why).
2. **Freeze** — No in-place mutation of frozen item labels/identities; fixes ⇒ new version + lineage.
3. **Lineage** — Each version declares predecessor (if any) and derivation notes.
4. **Changelog** — Required on version bump (adds/removes/label edits/slice changes/gate impact).
5. **Compatibility** — Schema incompat with evaluator contract ⇒ fail closed for blocking profiles.
6. **Reproducibility** — A run citing `dataset_version=X` must be interpretable against frozen X plus run metadata + judge version.
7. **Domain content** — Domain labels enter via datasets / Domain Packs only.
8. **Gate loosening** — Removing failing Core items or loosening labels is a governed review event.

### Responsibilities

| Role | Responsibility |
|------|----------------|
| Dataset curator | Draft, changelog, lineage |
| Approver | Approve/reject freeze; review gate-loosening |
| Evaluation architect | Schema fitness, tier/profile binding |
| Domain Pack owner | Domain label correctness |
| Release owner | Ensure Release profile pins approved freezes |

---

## Benchmark rules

1. Benchmarks follow the same lifecycle and immutability rules.
2. Benchmark versions are explicit identities (not ad hoc scrapes).
3. Cross-release comparability requires the same frozen benchmark version OR an explicit evolution bridge in the report.
4. Benchmarks carry tags for slice-compatible selection.
5. Evolution process: propose → impact review on champion baselines → approve → freeze → update Release pins → changelog → communicate incomparability windows.

---

## Acceptance

Contract review fails if:

- PR/Release profiles may pin Draft/unfrozen Core Golden silently
- Frozen datasets can be edited in place
- Benchmark compare claims omit version identity
- Changelog/lineage are optional for blocking-tier version bumps
)

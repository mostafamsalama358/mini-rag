# Contract: Publishing Semantics

**Feature**: 017-scalability-reliability | **Version**: 1.0.0  
**Normative for**: Persist & Index + Application (Ingest) publish step

---

## Purpose

Guarantee search visibility and exactly-once activation of Logical Document Versions.

---

## Visibility rule

For any Logical Document Identity, search observers MUST see:

- the current **Active Version**, or
- after successful publish, the **new Active Version** only.

Observers MUST NEVER see:

- a blend of old and new content,
- unpublished in-flight material,
- dual Active Versions for the same identity.

---

## Exactly-once publish

| Guarantee | Rule |
| --------- | ---- |
| Single activation | Each `(logical_document_id, version_id)` activates at most once |
| Retry safety | Retries/resumes after successful Publish Completion are publish no-ops |
| Duplicate completion | Duplicate completion signals MUST NOT create a second activation |
| Determinism | Publish Completion identity is stable for that successful activation |

---

## Replacement lifecycle

1. New version is prepared while prior Active Version (if any) remains visible.
2. Integrity gates pass on the new version’s produced content, searchable output, metadata completeness, and consistency.
3. Publish Completion switches Active Version atomically; prior version becomes Superseded.
4. On fail/cancel/timeout before successful publish: Active Version unchanged; unpublished material never searchable.

---

## Fully committed

A version is **fully committed** only when all hold:

1. Owning job is `Completed` or `Completed With Warnings`
2. Version status is `active`
3. Searchable state observes that version
4. Metadata required for retrieval/citation completeness agrees with that version

---

## Idempotency unit

`(Logical Document Identity, Logical Document Version)`

Duplicate submissions for the same unit MUST NOT create duplicate Active searchable content.

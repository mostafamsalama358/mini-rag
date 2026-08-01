# Contract: Compatibility (Frozen Answer API)

**Feature**: 020-pharmacy-recommendation | **Date**: 2026-07-22  
**Authority**: Feature 015 api-stability / 016 ADR-003; [ADR-020-001](../governance/adr-020-001-recommendation-as-capability.md)

---

## Normative

1. Recommend-mode MUST use the existing endpoint:
   ```text
   POST /api/v1/nlp/{project_id}/answer
   ```
2. Frozen **request** fields remain: `text`, `limit`, `session_id`, `metadata_filter` (names/optionality/defaults unchanged).
3. Frozen **success/clarification response** fields remain: `signal`, `answer`, `needs_clarification`, `full_prompt`, `chat_history` (and existing error shapes).
4. Recommendation content MUST appear in `answer` (and clarification via existing `needs_clarification` / clarification `signal` values).
5. MUST NOT add a dedicated Recommendation API or recommend-only route as the production path.
6. MUST NOT require clients to consume new mandatory wire fields for recommend-mode v1.
7. Internal Recommendation Trace / Quality Context MAY exist off the frozen public field set (diagnostics), consistent with 018—without renaming frozen fields.

## Explicitly out of contract

- New `recommendations[]` (or similar) public field — requires a **separate versioned API change**, not implied by 020.
- Recommendation Service RPC/HTTP surface.

## Compatibility tests (planning)

- Contract tests: answer schema unchanged with recommend-intent fixtures.
- Shadow diff (if used): content may change; field names/shapes must not.

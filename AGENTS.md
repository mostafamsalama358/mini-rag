<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/022-unified-skill-runtime/plan.md`

**M0 freeze**: No new parallel production implementations for the same concern without a superseding ADR (`specs/016-architecture-consolidation/governance/m0-freeze.md`). Dual-path Answer traffic is transitional via 015 until sole-owner gates pass. Feature 017 hardens the sole ingest path only. Feature 018 extends answer/retrieval quality contracts without new owners or parallel paths. Feature 019 extends evaluation architecture (offline/online/monitoring) without creating a production evaluation stage or parallel answer/retrieval path. Feature 020 extends pharmacy Domain Pack recommendation as a capability on the sole Answer/Retrieval path — no Recommendation Service, Recommendation API, parallel path, or new sole owner (ADR-020-001). Feature 021 extends Domain Skills as a Domain Pack capability on the sole Answer/Retrieval path — explicit client Skill selection, Metadata Profiles (`SkillFilterProfile`), entity-only parse under Skill; no Skill Service, parallel path, or new sole owner (ADR-021-001); no server-side skill/intent/alias routing. Feature 022 completes Unified Skill Runtime — Skills configure the unified pipeline only (ADR-022-001); no legacy Skill executor, separate Skill runtime, dual Skill runtime, or Skill-specific pipelines; enforceable architecture tests; no new sole owner.

**Governance**: Capability/ownership/lifecycle changes MUST use `specs/016-architecture-consolidation/checklists/architecture-review.md` (or an exception ADR). Answer/retrieval quality contract changes MUST also use `specs/018-rag-quality-architecture/checklists/quality-architecture-review.md` before accepting parallel quality paths or new quality owners. Evaluation architecture changes should follow `specs/019-rag-evaluation-framework/` contracts (metric ownership, profiles, dataset/benchmark governance) and must not violate 016 sole-owner rules. Pharmacy recommendation capability changes must stay corpus-bounded Domain Pack extensions under 016/018, follow `specs/020-pharmacy-recommendation/contracts/`, and use 019 for recommend-mode eval profiles. Domain Skill changes must follow `specs/021-domain-skill-framework/contracts/` and Unified Skill Runtime rules under `specs/022-unified-skill-runtime/contracts/`, stay on the sole path (ADR-021-001 / ADR-022-001), and use additive `skill_id` without breaking frozen `/answer` response fields (015). Find owners in `specs/016-architecture-consolidation/governance/`, `specs/018-rag-quality-architecture/governance/`, and evaluation contracts under `specs/019-rag-evaluation-framework/contracts/` — not by folder archaeology.

Related:
- `specs/022-unified-skill-runtime/` — **active**; Unified Skill Runtime: Skills as configuration for the unified pipeline (ADR-022-001); remove legacy Skill bypass and QueryPlan bridge; immutable SkillExecutionContext; declarative PipelineBuilder; true Strategy Registry plugins; God-object elimination; enforceable `test_022_*` architecture gates; API/UI/Skill ID compatibility. Artifacts: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`, `governance/adr-022-001-skills-as-unified-runtime-configuration.md`, `checklists/requirements.md`.
- `specs/021-domain-skill-framework/` — **dependency**; Domain Skill Framework baseline: explicit UI/API Skill selection, per-domain Skill registry, Metadata Profiles (`SkillFilterProfile`), entity-only query parse under Skill (ADR-021-001). Artifacts: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`, `governance/adr-021-001-skills-as-domain-pack-capability.md`, `checklists/requirements.md`, `tasks.md`.
- `specs/020-pharmacy-recommendation/` — **related**; Pharmacy Recommendation Capability: under 021/022, recommend-mode is reached only via explicit recommend-capable Skills (e.g. Alternatives) — Domain Pack extension on sole Answer/Retrieval path (ADR-020-001).
- `specs/019-rag-evaluation-framework/` — **related**; RAG Evaluation Framework: hosts recommend-mode and future skill-scoped eval profiles.
- `specs/018-rag-quality-architecture/` — **related**; RAG Quality Architecture; skill_id/profile_id as trace attributes.
- `specs/017-scalability-reliability/` — **related (orthogonal)**; sole-path ingest hardening.
- `specs/016-architecture-consolidation/` — **governance baseline**; sole production path; M0 freeze; frozen external answer contract.
- `specs/015-unified-pipeline-migration/` — **dependency (cutover vehicle)**; unified pipeline becomes native Skill runtime under 022; frozen `/answer` response contract; additive request `skill_id`.
- `specs/014-answer-quality/` — **dependency (semantic seed)**; Faithfulness/Completeness/coverage semantics preserved.
- `specs/013-answer-generation/` — stage library; Skill prompt binding under 021/022.
- `specs/012-context-builder/` — stage library; ownership subject to 016.
- `specs/011-evidence-orchestrator/` — stage library; ownership subject to 016.
- `specs/010-retrieval-engine-v2/` — retrieval candidate; consumes Skill profile filters / strategy plugins under 021/022.
- `specs/009-retrieval-planner/` — planning concern library; MUST NOT re-infer skill when `skill_id` bound.
- `specs/004-semantic-query-parser/` — under Skill-bound mode: entity/slot extraction only.
- `specs/006-document-intelligence-pipeline/` — ingest dependency for 017; orthogonal to Skill runtime.
- `specs/002-field-registry/` — Domain Packs extension model; Skills + profiles under `src/fields/{domain}/`.
<!-- SPECKIT END -->

<!-- lean-ctx -->
## lean-ctx

lean-ctx is active — the MCP tools replace native equivalents.
Full rules: LEAN-CTX.md (open on demand — do not auto-load).
<!-- /lean-ctx -->

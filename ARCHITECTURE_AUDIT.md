# mini-rag / AlgoRAG — Principal Staff Engineering Architecture Audit

**Date:** 2026-07-15
**Scope:** Full codebase review of specs 006–014 (Document Intelligence, Chunking, Knowledge Representation, Query Parser, Retrieval Planner, Retrieval Engine, Evidence Orchestrator, Context Builder, Answer Generation, Answer Quality) plus all supporting infrastructure (`src/routes`, `src/services`, `src/repositories`, `src/models`, `src/stores`, `src/tasks`, `src/utils`, `src/helpers`, `src/fields`).
**Method:** Read-only static audit. Every claim below is backed by a file/class/function citation. Findings are deduplicated across seven independent deep-dive passes (Document Intelligence & Chunking; Knowledge & Query Parser; Retrieval Planner & Engine; Evidence Orchestrator & Context Builder; Answer Generation & Answer Quality; cross-cutting infrastructure; testing/spec-consistency).
**Reference frame:** production-grade, generic, domain-agnostic retrieval platform in the spirit of NotebookLM-class architectures (not feature parity).

---

## 0. Executive Summary — Read This First

This codebase contains **two parallel RAG systems that do not talk to each other**:

1. **The "SpecKit" stack** (`src/core/retrieval_planner`, `src/core/retrieval_engine`, `src/core/evidence_orchestrator`, `src/core/context_builder`, `src/core/answer_generation`, `src/core/answer_quality`, `src/core/knowledge`) — cleanly layered, interface-driven, well-unit-tested Python libraries built against specs 008–014.
2. **The production system** (`src/services/rag/answer_service.py`, `src/services/rag/rag_service.py`, `src/core/retrieval/*`, `src/core/query_parser`, `src/utils/rerank/*`) — the code that actually runs when a user hits `/api/v1/nlp/*`.

**`grep`-level fact:** `src/services/rag/answer_service.py` never imports `retrieval_planner`, `retrieval_engine`, `evidence_orchestrator`, `context_builder`, or `answer_generation`. `src/core/knowledge` is imported by nothing outside its own package. Only `query_parser` (spec 004) is actually wired into production.

This means specs 009–014 — six specs, thousands of lines of production-quality-*looking* code, hundreds of unit tests — are **libraries with no callers**. Every quality property claimed for those specs (grounding, budget-aware context assembly, conflict disclosure, offline evaluation gating) is **true of the library in isolation and false of the product**. This is the single most important finding in this audit: it invalidates any claim that "specs 006→014 have been completed" in the sense of a working, integrated platform. They are complete in the sense of "six well-tested SDKs sitting on a shelf."

Everything else in this report — dead-code duplication, stub retrievers, gameable evaluation metrics, missing auth — is a symptom of the same underlying process failure: **specs were implemented bottom-up as isolated modules with contract tests, and integration was never scheduled as a task.** Fix the integration gap first; most other findings become either moot (if the module is replaced during integration) or trivially higher-priority (if the module is kept).

Full findings follow, organized by the 15 requested focus areas. Scores and a prioritized roadmap are at the end.

---

## 1. Architecture

### ARCH-01 — Two independent, non-interoperating RAG stacks
- **Severity:** Critical
- **Category:** Architecture
- **Location:** `src/services/rag/answer_service.py`, `src/services/rag/rag_service.py` (production) vs. `src/core/retrieval_planner/`, `src/core/retrieval_engine/`, `src/core/evidence_orchestrator/`, `src/core/context_builder/`, `src/core/answer_generation/`, `src/core/knowledge/` (SpecKit libraries)
- **Problem:** Production answer flow is: `NLPController.search_vector_db_collection` → `core.retrieval.hybrid_rrf` / `core.retrieval.focus` → `utils.rerank` → hand-built prompt in `answer_service.py`. None of the six newer modules are invoked. `RetrievalResult` even exists as two incompatible types (`core.retrieval_engine.models.RetrievalResult` vs. a local dataclass in `answer_service.py`).
- **Impact:** Today: doubled maintenance surface, confused onboarding, quality guarantees that don't apply to real traffic. Future: every new capability built into the SpecKit stack (clarification gating, conflict disclosure, budget-aware compression, offline quality gating) delivers zero user value until a deliberate integration project runs. Risk of an engineer "cleaning up" `core.retrieval` because it looks superseded, breaking production.
- **Recommended Fix:** Run an explicit **Integration Epic**: wrap existing vectordb/LLM clients as adapters conforming to the SpecKit `Retriever`/`LLMInterface` protocols, replace the body of `answer_service.answer_question` with `Parser → Planner → Engine → Orchestrator → ContextBuilder → AnswerGeneration`, behind a feature flag, with a regression test asserting the new path is invoked. Do not add further features to either stack until this lands.

### ARCH-02 — Domain leakage into "generic" core modules
- **Severity:** High
- **Category:** Architecture
- **Location:** `src/services/process_service.py` (`brand_name` passthrough, `field_resolution.LEGACY_ENTITY_KEY_PRIORITY`), `src/core/query_parser/parser.py::_heuristic_plan_from_query` (pharmacy keyword tables + "Parse the pharmacy question…" default prompt), `src/core/knowledge/extractors/structural.py::_MEAS_RE` (clinical units `mg/mcg/mmHg/IU`), `src/services/rag/answer_service.py` (`if query_plan.field == "interactions"` branches)
- **Problem:** The field-registry pattern (`src/fields/{generic,pharmacy,legal}`) is meant to isolate domain vocabulary in YAML. Multiple core/service modules hardcode pharmacy-specific fallbacks, regexes, and branches instead.
- **Impact:** "Generic" core is not actually generic; onboarding a new vertical (e.g. insurance, supermarket) requires editing shared code, not just adding a YAML pack — directly contradicting the field-registry value proposition.
- **Recommended Fix:** Move all domain keyword tables/regex/branches into pack YAML (`entity_key_aliases`, `fallback_rules`, `measurement_patterns`); core code must fail closed (return `field=unknown` / empty) rather than guess a domain.

### ARCH-03 — Dead/duplicated implementations left in place instead of removed or clearly quarantined
- **Severity:** High
- **Category:** Technical Debt
- **Location:** `src/core/retrieval/` (live legacy RRF/expansion) vs `src/core/retrieval_engine/` (SpecKit v2); `src/core/document_intelligence/chunk_mapper.py` + `src/core/chunking/engine.py::row_chunk_*` vs `src/core/chunking/strategies/semantic_structural.py`; two `DegradationReason` Literal definitions (`document_intelligence/errors.py` and `model.py`)
- **Problem:** Modules are documented as "deprecated" or "Phase 5 deletes" in code comments but are still the actively imported production path (`core.retrieval`). Others (`chunk_mapper`) are legacy shims left reachable alongside the new strategy.
- **Impact:** Bug fixes applied to one implementation silently don't apply to the other; new engineers cannot tell which code path is authoritative without reading call graphs.
- **Recommended Fix:** For each duplicate pair, pick one canonical implementation, delete or explicitly gate the other behind a `@deprecated`-style import error, and add a lint rule/CI check that fails if the deprecated module gains new imports.

### ARCH-04 — Clean-Architecture dependency-direction violations in "core"
- **Severity:** High
- **Category:** Architecture
- **Location:** `src/core/query_parser/parser.py` imports `services.FieldRegistry.FieldProfile` and `stores.llm.errors.VertexGenerationError`; `src/core/context_builder/compression/llm_compressor.py` imports `stores.llm.LLMProviderFactory` directly
- **Problem:** `core/` is meant to be the domain/application layer with infrastructure injected via interfaces (per AGENTS.md / spec conventions). These modules import concrete infrastructure (`stores/`) and service-layer types directly.
- **Impact:** Core logic cannot be unit tested or reused without infrastructure present; infrastructure changes (swap LLM vendor) ripple into core; violates DIP.
- **Recommended Fix:** Define core-owned Protocols (`ISummarizer`, `IFieldProfile`, `IGenerationError`) and inject concrete adapters at the composition root (service layer), never import `stores`/`services` from `core`.

### ARCH-05 — Registries are static factories, not open extension points
- **Severity:** Medium
- **Category:** Design
- **Location:** `AnswerQualityRegistry.default_runner`, `AnswerGenerationRegistry.build`, `EvidenceOrchestratorRegistry.build_orchestrator` (ignores config, `_ = config`), `ChunkingRegistry` (import-time singleton in `chunking/strategies/__init__.py`)
- **Problem:** "Registry" naming implies open/closed extensibility (config selects implementation), but most registries hardcode concrete classes in Python, and at least one (`EvidenceOrchestratorRegistry`) explicitly discards the config object that would drive selection.
- **Impact:** Swapping a scorer/compressor/deduplicator implementation requires a code change and redeploy, not a config change — undermining the entire point of a plugin registry, and blocking safe experimentation (A/B of faithfulness scorers, etc.).
- **Recommended Fix:** Registries should map config string → constructor, validated against a whitelist, resolved at composition-root time; construct explicit `Registry` instances (not import-time global singletons) so multiple apps/tests don't share state.

### ARCH-06 — Knowledge Representation module (spec 008) is architecturally orphaned
- **Severity:** Critical
- **Category:** Architecture
- **Location:** `src/core/knowledge/**`; `src/services/rag/answer_service.py` (no import); `src/tasks/data_indexing.py` (no invocation)
- **Problem:** A complete typed knowledge-unit/relationship extraction pipeline exists with its own pipeline, models, discovery, normalization, validation, and a stub graph-representation strategy — but nothing in the indexing or answer path ever constructs a `KnowledgePackage`.
- **Impact:** All of spec 008's engineering investment currently produces zero product value; it is pure maintenance cost. This is the most extreme instance of Finding ARCH-01.
- **Recommended Fix:** Either wire one concrete consumer (e.g., planner reads units by entity/field, or units are embedded alongside chunks for retrieval) before any further knowledge-representation work, or explicitly mark it "research/deferred" in AGENTS.md instead of listing it as a completed dependency.

---

## 2. Document Intelligence

### DI-01 — Three coexisting chunking/parsing pipelines instead of one canonical path
- **Severity:** Critical
- **Category:** Architecture
- **Location:** `src/services/process_service.py::ProcessController.process_file_content` (L259–377), `src/core/document_intelligence/chunk_mapper.py::map_elements_to_chunks`, `src/core/chunking/engine.py::row_chunk_*`
- **Problem:** Spec 007 mandates one Boundary Decision Pipeline. In practice: DocumentModel-attached files go through `SemanticStructuralChunkingStrategy`; some paths still call the legacy `map_elements_to_chunks`; non-model content falls back to a bare `RecursiveCharacterTextSplitter`.
- **Impact:** Behavior (and embedding text, since one path prefixes `[file_id | sheet]` and the other doesn't) depends on which code path executed, making retrieval quality non-deterministic per document type.
- **Recommended Fix:** Single ingestion entrypoint: `DocumentModel → registered ChunkingStrategy → ChunkSet`, always. Delete or quarantine the legacy mapper/splitter behind a feature flag with a failing test if referenced from production.

### DI-02 — XLSX/CSV parsers load entire file into memory; documented batching is dead code
- **Severity:** Critical
- **Category:** Scalability
- **Location:** `src/core/document_intelligence/parsers/xlsx_parser.py::XlsxDocumentParser.parse` (L76–81), `_ROW_BATCH_SIZE` batch check body is literally `pass` (L64–66); `csv_parser.py::pd.read_csv` (L28)
- **Problem:** `pd.read_excel(sheet_name=None)` materializes every sheet and every row into one `StructuralElement` list in memory; the code comment claims streaming batching, but the branch that should flush a batch does nothing.
- **Impact:** Large pharmacy/retail catalogs (tens of thousands of rows) will OOM-kill Celery workers; there is no way to ingest a file larger than available worker memory.
- **Recommended Fix:** Stream with `openpyxl` read-only mode / chunked CSV reads; yield element batches to the chunking stage instead of building one giant list; add a large-file fixture test that asserts bounded peak memory.

### DI-03 — Degraded-parse fallback usually yields an empty, useless document
- **Severity:** Critical
- **Category:** Reliability
- **Location:** All parsers raising `DocumentIntelligenceDegraded` without `best_effort_text` (`xlsx_parser.py` L92–95, `csv_parser.py` L34, `pdf_parser.py` L43); `fallback.py::build_fallback_model` (L24–33)
- **Problem:** The exception type supports carrying recovered text for degraded documents, but no parser ever populates it; the fallback builder then produces a model with `elements=[]`.
- **Impact:** Ingestion silently "succeeds" (status = degraded) while indexing zero retrievable content — a document appears processed but is invisible to retrieval, with no loud signal to operators.
- **Recommended Fix:** On any soft failure, always attach best-effort raw text (decoded bytes, `to_csv()`, page-concatenated PDF text). Add an integration test: malformed-but-readable file → degraded model with non-empty text and ≥1 chunk.

### DI-04 — Hard parser failures are swallowed into `None`, masquerading as "no content"
- **Severity:** High
- **Category:** Reliability
- **Location:** `src/services/process_service.py::_parse_document_model` (L102–106): `except Exception: return None`
- **Problem:** After re-raising known transient errors, any unexpected exception is converted to "no document model" rather than propagated as an ingestion failure.
- **Impact:** Corrupt/unsupported files appear as missing content instead of failed jobs; operators cannot distinguish "empty document" from "our parser crashed."
- **Recommended Fix:** Propagate unexpected exceptions as a distinct ingestion-failure status; only map the documented `DocumentIntelligenceDegraded` type to the fallback path.

### DI-05 — Chunk validation is advisory only; failed chunk sets are indexed anyway
- **Severity:** High
- **Category:** Reliability
- **Location:** `process_service.py::process_file_content` (L301–324) never inspects `validation_report.status`
- **Problem:** `ChunkValidator` can return `status="fail"` (empty chunks, oversize violations, broken parent/child links), but the ingestion path indexes the chunk set regardless.
- **Impact:** Broken/garbage chunks enter the vector store and are retrievable, degrading answer quality with no operator visibility outside unit tests.
- **Recommended Fix:** Gate indexing on `validation_report.status != "fail"`; quarantine failing chunk sets; persist the report and alert.

### DI-06 — PDF structural understanding is a whitespace heuristic, not real layout parsing
- **Severity:** High
- **Category:** Design
- **Location:** `src/core/document_intelligence/parsers/pdf_parser.py::_looks_like_table_block` (regex `\S+\s{2,}\S+` / tabs, L13–17); one `section` per page otherwise
- **Problem:** No heading, list, code-block, or quote detection; tables are guessed from whitespace runs. Docling is used only for OCR page images (`utils/docling_ocr.py`), not as a layout-aware `DocumentConverter`.
- **Impact:** Semantic/structural chunking has almost no real hierarchy signal for the most common enterprise format (PDF); the "extended element types" (`heading`, `list`, `code-block`, `figure-placeholder`) exist only in synthetic test fixtures, never in production output.
- **Recommended Fix:** Introduce a pluggable layout-provider interface; use a real layout model (full Docling pipeline, or equivalent) as the primary PDF path, keeping the whitespace heuristic only as last-resort fallback. Add PDF parser unit tests — currently there are none for the happy path.

### DI-07 — Canonical structural types are declared but never produced by any real parser
- **Severity:** High
- **Category:** Technical Debt
- **Location:** `src/core/document_intelligence/model.py::CANONICAL_ELEMENT_TYPES` (heading, list, list-item, code-block, quote, figure-placeholder) vs. `parsers/*.py`
- **Impact:** Half of the document model's declared vocabulary is exercised only by hand-built test fixtures; production ingestion never touches that code, so bugs there are invisible until a real parser is written.
- **Recommended Fix:** Either implement producers for these types or mark them "reserved/unsupported" in the model until a parser exists; add a contract test asserting every canonical type has ≥1 real-parser fixture.

### DI-08 — Table-row elements can never be grouped, defeating YAML-configurable chunking
- **Severity:** Critical
- **Category:** Design
- **Location:** `src/core/chunking/evaluator.py::SemanticBoundaryEvaluator.evaluate` (L109–112) unconditionally sets `table_integrity = False` for any two adjacent `table-row` elements
- **Problem:** Field-pack YAML exposes `element_mapping["table-row"].group: true` to allow merging short rows into one chunk, but the evaluator overrides this for every table-row pair regardless of config.
- **Impact:** The core promise of spec 006 ("YAML-only domain differences") is false specifically for tabular content — the highest-value content type for structured business documents (price lists, dosage tables, schedules).
- **Recommended Fix:** Redefine table integrity as "same parent table / same `parent_id`," not "never merge two rows"; honor the pack's `group` flag; add a golden test asserting multi-row chunks when `group: true`.

### DI-09 — TXT parser collapses entire files into a single element without pack patterns
- **Severity:** High
- **Category:** Design
- **Location:** `src/core/document_intelligence/parsers/text_parser.py` (L27–34) calls `split_at_structural_boundaries(text)` with no `patterns`; `structural/engine.py` returns `[stripped]` (the whole file) in that case
- **Impact:** The simplest, most common format (plain text) gets the worst structural fidelity — one giant paragraph, forcing character-based oversized splitting downstream.
- **Recommended Fix:** Default generic segmentation on blank lines regardless of pack patterns; treat structural patterns as additive boundaries, not the only source of splits.

### DI-10 — Format registry is incomplete and duplicated across three sources of truth
- **Severity:** High
- **Category:** Maintainability
- **Location:** `ProcessingEnum` (4 extensions only), `parsers/__init__.py::_build_default_registry`, `process_service.py::get_file_content` if/elif, `ChunkingProfile.by_extension` YAML (still uses legacy `row|page|character` vocabulary)
- **Impact:** Adding one new format (DOCX, HTML) requires touching 3–4 unrelated files; operators can misconfigure `by_extension` believing it selects the modern chunking strategy when it actually selects a legacy splitter.
- **Recommended Fix:** One `extension → parser_id` registry; remove `ProcessingEnum` from the document-intelligence decision path; separate and rename the YAML key that controls parser selection from the one that controls chunking strategy.

---

## 3. Chunking

### CHK-01 — Parent/child hierarchy is a heuristic heading stack, not the real document outline
- **Severity:** Medium
- **Category:** Design
- **Location:** `src/core/chunking/builder.py::_emit_chunk` / `_update_heading_stack` (L195–247)
- **Problem:** The heading stack *replaces* rather than nests, and "parent chunk" means "the last section-type chunk seen," ignoring `StructuralElement.parent_id`. XLSX rows never get a synthetic table parent at all.
- **Impact:** `heading_path` and parent/child relationships used for citation and retrieval-expansion do not reflect true nested document structure; multi-level heading queries will resolve to the wrong ancestor.
- **Recommended Fix:** Build the outline directly from `parent_id` + heading depth; synthesize per-sheet table parents for spreadsheet rows.

### CHK-02 — Chunk validator rules are ineffective because upstream never populates the fields they check
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `src/core/chunking/validator.py` (L45–53) checks `metadata["lineage_section_ids"]`, which `builder.py` never sets
- **Impact:** False confidence — the "cross-section merge" validation rule can never fire, so the exact defect class it exists to catch is undetected.
- **Recommended Fix:** Populate `lineage_section_ids` from builder context so the rule is live; redefine "orphaned heading" detection to check for absence of following sibling content, not a near-tautological string check.

### CHK-03 — Chunk sizing is character-based only; token/overlap semantics are inconsistent
- **Severity:** Medium
- **Category:** Scalability
- **Location:** `ChunkingStrategyConfig.max_chars`; `builder.py::_OversizedSplitter` (overlap only applied on the char-fallback path, not paragraph/sentence splits)
- **Problem:** Downstream (context builder, LLM prompt) budgets in *tokens*; chunking budgets in *characters*. Non-Latin scripts and code have very different char:token ratios, silently causing over/under-sized chunks relative to the actual LLM window.
- **Recommended Fix:** Support an injectable token counter in chunk configuration mirroring the one already built for evidence orchestration/context builder; apply overlap consistently across all split strategies.

### CHK-04 — Strategy registry is an import-time global singleton
- **Severity:** Low
- **Category:** Maintainability
- **Location:** `src/core/chunking/strategies/__init__.py` (registers on import); `registry.py` module-level globals
- **Impact:** Parallel test runs or multiple app instances in one process can cross-contaminate strategy registrations.
- **Recommended Fix:** Build an explicit `ChunkingRegistry` instance at the composition root instead of relying on import side effects.

### CHK-05 — Two independent chunk-rendering implementations produce different embedding text for the same content
- **Severity:** Medium
- **Category:** Maintainability
- **Location:** `chunk_mapper.py::_render_element`/`_split_oversized` vs `builder.py::_render_element`/`_OversizedSplitter`; `chunking/engine.py` prefixes `[file_id | sheet]` onto chunk text while the DocumentModel path does not
- **Impact:** Retrieval quality (embedding similarity) differs for functionally identical content depending on which legacy/new code path processed it — an invisible, non-reproducible quality variance.
- **Recommended Fix:** One `ElementRenderer` shared by all callers; move any "display prefix" concerns into citation templates, never into the embedded/chunked text itself.

---

## 4. Knowledge Representation

*(See also ARCH-06 — the module is unwired from production; findings below assess it as a standalone library.)*

### KR-01 — `semantic_content`/`participants` are untyped free-form dicts, not a real ontology
- **Severity:** High
- **Category:** Design
- **Location:** `src/core/knowledge/models.py::KnowledgeUnit.semantic_content/participants`; `extractors/structural.py::_semantic_content`
- **Impact:** Each extraction strategy invents its own shape ad hoc; there is no way to reliably query "all measurements of X" or resolve participants (drug/person/org) across strategies — undermining the stated goal of being "graph-ready."
- **Recommended Fix:** Define per-`KnowledgeUnitType` schemas (Pydantic or JSON Schema in field packs), validated at extraction time; keep free-form `dict` only as a documented escape hatch.

### KR-02 — Relationship vocabulary is mostly aspirational; the discoverer only emits structural (reading-order) edges
- **Severity:** High
- **Category:** Design
- **Location:** `models.py::KnowledgeRelationshipType` (7 types incl. `dependency`, `equivalence`, `contradiction`, `derivation`) vs `discovery/structural.py::generate_candidates` (only emits `sequence`, `containment`, `elaboration`)
- **Impact:** Packages look graph-rich but the edges are adjacency-in-document artifacts, not semantic relationships — a "knowledge graph" that is really just a linked list with fancy labels. Any downstream graph reasoning will over-connect adjacent trivia and miss actual semantic links (contradictions, dependencies).
- **Recommended Fix:** Either implement semantic discoverers behind the same interface or shrink the advertised vocabulary to match what's implemented — don't let the type system claim capabilities the code doesn't have.

### KR-03 — Knowledge extraction is strictly document-local; no cross-document entity resolution
- **Severity:** Critical
- **Category:** Scalability
- **Location:** `src/core/knowledge/assembly.py::KnowledgePackageMetadata.asset_id` (one package per one asset); `normalizers/rule_based.py` dedups only within one `ChunkSet`
- **Impact:** Cannot answer "what does every leaflet say about drug X" via the knowledge layer; a real knowledge graph needs corpus-level entity identity, which does not exist anywhere in the pipeline.
- **Recommended Fix:** Add a corpus-level entity-resolution stage downstream of per-document extraction, mapping surface forms to stable cross-document entity IDs.

### KR-04 — Graph representation is a stub; the experimental graph retriever expects an API the repository doesn't implement
- **Severity:** High
- **Category:** Architecture
- **Location:** `representation/base.py::StubGraphRepresentationStrategy`; `retrieval_engine/retrievers/graph.py` expects `repo.traverse`/`repo.search`, which `KnowledgePackageRepository` doesn't provide; `fields/*/knowledge_representation.yaml` (`representation_strategies: []` by default)
- **Impact:** "Graph readiness" is currently a documented intention with no working implementation anywhere in the stack.
- **Recommended Fix:** Implement one real traversal-capable store (or explicitly rename the experimental retriever to avoid implying graph capability) before investing further in discoverer breadth.

### KR-05 — Citations from the knowledge layer omit page/span; provenance requires re-joining the source DocumentModel
- **Severity:** High
- **Category:** Reliability
- **Location:** `models.py::EvidenceReference` (chunk/element/document-model/asset IDs only); page number lives on `pdf_parser.py` element `provenance` and is never copied over
- **Impact:** A consumer holding only a `KnowledgePackage` cannot say "page 12" without also loading and joining the original `DocumentModel` — a silent information-loss point if that model isn't co-persisted.
- **Recommended Fix:** Denormalize `page`/char-span onto `EvidenceReference` at extraction time.

### KR-06 — Failed validation still returns a usable-looking package by default
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `models.py::KnowledgeExtractionConfig.fail_on_error` defaults `False`; `pipeline.py::run`
- **Recommended Fix:** Default `fail_on_error=True` for production profiles; never persist a `status=="failed"` package as canonical.

### KR-07 — New unit/relationship types require core code edits, breaking the "YAML-only" extensibility promise
- **Severity:** Medium
- **Category:** Extensibility
- **Location:** `models.py` Literal types; `validation.py::_rule_recognized_unit_type`
- **Recommended Fix:** Load allowed vocabulary from field-pack YAML (unioned with core defaults); keep extraction *logic* as strategy plugins, but let vocabulary be config-driven.

---

## 5. Query Planning

This area spans two modules: `src/core/query_parser` (spec 004, **wired into production**) and `src/core/retrieval_planner` (spec 009, **not wired into production** — see ARCH-01).

### QP-01 — Pharmacy heuristics are hardcoded into the deterministic core parser
- **Severity:** Critical
- **Category:** Architecture
- **Location:** `src/core/query_parser/parser.py::_heuristic_plan_from_query` (L66–116, maps Arabic/English keywords to `strengths`/`dosage`/`interactions`); default prompt text literally says "Parse the **pharmacy** question…" (L167–169)
- **Problem:** This is the fallback path invoked whenever the LLM call fails or returns unparseable JSON — i.e., exactly the failure mode a domain-agnostic core is supposed to degrade gracefully through.
- **Impact:** Legal/generic/any-other-domain deployments silently get pharmacy-shaped fallback plans on LLM failure; core cannot be domain-agnostic while this exists.
- **Recommended Fix:** Remove all domain keyword tables and the default prompt's domain reference from core; drive the fallback exclusively from pack-declared `fallback_rules`, defaulting to `field=unknown` plus catalog-entity inference when no pack rule matches.

### QP-02 — Entity grounding silently no-ops when the catalog is empty or the pack disables it
- **Severity:** High
- **Category:** Reliability / Security
- **Location:** `src/core/query_parser/grounding.py::ground_entity` (L216–267); `src/fields/legal/parser.yaml` (`entity_grounding.enabled: false`); `answer_service.py::_load_catalog_for_parser` returns `([], {})` when no metadata keys configured
- **Impact:** The spec's safety property — "ungrounded entities must trigger clarification" — silently fails open in exactly the misconfiguration cases most likely in a new deployment (no catalog wired up yet). Hallucinated LLM-invented entities proceed straight to retrieval.
- **Recommended Fix:** Fail closed: if grounding is enabled but the catalog is empty, treat every entity as ungrounded (force clarification) rather than skip the check.

### QP-03 — JSON extraction has no repair step and a shallow single-level regex fallback
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `src/core/query_parser/json_extract.py::extract_json_object` (L8–37)
- **Impact:** Trailing commas, markdown-fenced output, or nested-object drift from the LLM provider fall through to the pharmacy-flavored heuristic fallback (QP-01) more often than necessary.
- **Recommended Fix:** Strip markdown fences, apply a lightweight JSON-repair pass, prefer native provider JSON mode over text-mode extraction wherever available.

### QP-04 — Query parser has zero dedicated tests despite spec 004 marking its test tasks complete
- **Severity:** Critical
- **Category:** Testing
- **Location:** `specs/004-semantic-query-parser/tasks.md` marks unit/golden test tasks `[x]`; `tests/unit/core/query_parser/` and any `tests/golden/query_parser/*` **do not exist** in the repository
- **Impact:** The single production-wired module with LLM-driven parsing, grounding, and clarification — arguably the highest-risk component in the whole system — has no regression safety net at all. Task-completion checkmarks are actively misleading.
- **Recommended Fix:** Restore/author unit tests for `json_extract`, `grounding`, `normalize`, `validator`, and a mocked-LLM golden suite (Arabic + English, ≥30 cases) before touching this module again; add a CI check that fails if a `src/core/<x>` package has zero matching `tests/unit/core/<x>/` files.

### PLAN-01 — Retrieval planner is a fully-built, unit-tested library that production never calls
- **Severity:** Critical
- **Category:** Architecture
- *(This is the retrieval_planner instance of ARCH-01; see there for detail.)*

### PLAN-02 — Clarification is a data flag, not an orchestration guarantee
- **Severity:** High
- **Category:** Reliability
- **Location:** `retrieval_planner/clarification/confidence_based.py` (returns `bool, question`); `retrieval_planner/pipeline.py` (L58–71) empties `strategies` on trigger but nothing stops the engine from "executing" an empty plan
- **Impact:** Even inside the SpecKit stack alone, "must not begin retrieval" is only an invariant on data, not an enforced control-flow gate — a caller that doesn't check the flag gets an empty-but-successful result instead of a clarification prompt.
- **Recommended Fix:** Engine should raise a typed `ClarificationRequiredError` when `clarification_required=True`, forcing callers to handle it explicitly; add a host-layer (API) gate that converts this into a clarification response to the user.

### PLAN-03 — Intent classification is permanently rule-based with no ML/LLM path, and confidence scores are hardcoded constants
- **Severity:** High
- **Category:** Design
- **Location:** `retrieval_planner/intent/rule_based.py` (L11–24, confidence values `1.0/0.8/0.6/0.4` are literals, not calibrated); English-centric regex patterns
- **Impact:** Mis-routed strategies for anything outside the pattern list; clarification false positives/negatives are structural, not tunable.
- **Recommended Fix:** Keep rules as a fast path but add an optional LLM/ML classifier behind the existing `IIntentClassifier` interface; calibrate confidence from signal agreement instead of static constants; move patterns into pack YAML.

### PLAN-04 — Strategy selection ignores the entities and filters already extracted by the plan
- **Severity:** Medium
- **Category:** Design
- **Location:** `retrieval_planner/strategies/config_driven.py::select` (L20–27, `del entities, filters`)
- **Impact:** Comparative queries with rich entity sets and navigational queries with heavy filters get the exact same static strategy list as bare queries — underusing information the planner already computed.
- **Recommended Fix:** Add additive rules (e.g., detected table/tabular filters ⇒ ensure the structured/table strategy is included).

---

## 6. Retrieval Engine

### RET-01 — Retrievers are empty shells that silently return `[]` when no store is injected
- **Severity:** Critical
- **Category:** Reliability
- **Location:** `retrieval_engine/retrievers/{dense,sparse,metadata,structured,graph}.py` — all follow `if self._store is not None: ... else: return []`; `registry.py::register_defaults` wires `store=None` by default
- **Impact:** A pipeline built with `register_defaults()` alone "runs successfully" and returns zero candidates — indistinguishable from an empty corpus. This is a silent failure mode with no error surfaced.
- **Recommended Fix:** Require store injection at registry build time in non-test environments; raise `RetrieverMisconfiguredError` rather than degrading to empty results.

### RET-02 — Graph retrieval is not graph traversal
- **Severity:** High
- **Category:** Design
- **Location:** `retrieval_engine/retrievers/graph.py::GraphRetriever` (L18–47) — calls `repo.traverse`/`repo.search` with the raw query string; no multi-hop, no relation-type filters, no entity seeding from `plan.entities`
- **Impact:** Comparative/multi-hop queries requesting graph strategy either hit `retriever_not_found` (not registered by default) or a shallow single-hop search that provides none of the value multi-hop graph retrieval is meant to deliver.
- **Recommended Fix:** Implement real k-hop traversal seeded from plan entities with relation-type filters and path scoring, or rename the class to avoid overstating capability.

### RET-03 — Strategy vocabulary mismatch between planner and engine causes silent leg drops
- **Severity:** Critical
- **Category:** Reliability
- **Location:** Planner emits `table`/`document`/`graph` (`retrieval_planner/models.py`, `fields/generic/retrieval_planning.yaml`); engine registers `structured` (`retrieval_engine/models.py`, `fields/generic/retrieval_engine.yaml`); mismatch resolved via silent skip (`pipeline.py` L388–397, `retriever_not_found`)
- **Impact:** A correctly-planned tabular/navigational/comparative query loses legs it should have executed, with no hard failure — recall collapses invisibly.
- **Recommended Fix:** One shared strategy-name vocabulary/alias map used by both planner and engine defaults; fail loudly (not silently skip) when all preferred strategies for a plan are unavailable.

### RET-04 — Expansion and reranking default to no-ops in the new engine; real implementations exist only in the legacy path
- **Severity:** High
- **Category:** Architecture
- **Location:** `retrieval_engine/expansion/passthrough.py`, `retrieval_engine/reranking/passthrough.py` are the wired defaults (`registry.py` L94–101 actively *prefers* passthrough even if another expander is registered); real BGE/Cohere rerankers and multi-query expansion exist only under `utils/rerank/` and `core/retrieval/focus.py`, used by the legacy production path
- **Impact:** The SpecKit engine, if ever wired to production, would ship *without* the quality features (reranking, query expansion) production currently has via the legacy path — an unintentional regression waiting to happen at cutover time.
- **Recommended Fix:** Build adapters bridging `utils.rerank.RerankerInterface` → `IReranker` and `core.retrieval.focus` → `IQueryExpander`; fix the registry's passthrough preference bug; register real implementations by default.

### RET-05 — Fusion (RRF) is mathematically correct but destroys score provenance and mishandles empty IDs
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `retrieval_engine/fusion/rrf.py` (L24–48) — `model_copy(update={"raw_score": rrf_score})` overwrites the original per-retriever score; dedup keys purely on `chunk_id`, so multiple items with an empty/missing `chunk_id` silently merge
- **Recommended Fix:** Keep `rrf_score` as a separate field from the original score; require non-empty chunk identity or fall back to a composite key (doc+page+offset) as the legacy path already does.

### RET-06 — Sync store calls inside "async" retrievers can block the event loop
- **Severity:** High
- **Category:** Performance
- **Location:** All retrievers use `hasattr(result, "__await__")` to conditionally await; synchronous store calls run directly on the event-loop thread
- **Impact:** Under concurrent load, one slow synchronous vector/FTS call stalls every other in-flight request on that worker.
- **Recommended Fix:** Always dispatch synchronous store calls via `asyncio.to_thread`, or require async-only store implementations.

### RET-07 — No filter/limit pushdown to stores; unbounded in-memory fan-out
- **Severity:** High
- **Category:** Scalability
- **Location:** Retrievers pass `filters=context.filters` as an opaque tuple with no per-backend translation; `BudgetEnforcer` only trims lists **after** retrieval, not before (`budget/enforcer.py`)
- **Impact:** At scale (millions of chunks), retrieving unbounded candidate sets before capping in memory is a hard ceiling on both latency and cost; this architecture will not survive a 10–100x corpus growth.
- **Recommended Fix:** Per-backend filter compiler translating `QueryFilter` into native filter syntax; always pass `limit=max_candidates` to the store call itself, never just to the post-hoc trimmer.

### RET-08 — `core.retrieval` (the actual production algorithm layer) is undocumented as such and at risk of accidental deletion
- **Severity:** Medium
- **Category:** Technical Debt
- **Location:** `src/core/retrieval/__init__.py` / `engine.py` docstrings say "DEPRECATED... Phase 5 deletes," while `rag_service.py`/`answer_service.py`/`enrichment.py` actively import it
- **Recommended Fix:** Correct the docstrings immediately; this is a landmine for the next engineer who trusts the comment over the call graph.

---

## 7. Evidence Orchestration

### EO-01 — "Embedding" deduplication is not embedding-based by default
- **Severity:** High
- **Category:** Reliability
- **Location:** `evidence_orchestrator/deduplication/embedding_deduplicator.py::EmbeddingDeduplicator.deduplicate`; `registry.py` wires `embedding_provider=None` by default
- **Problem:** With no embedding provider injected (the default), the class silently falls back to character 3-gram Jaccard similarity (`_near_dedup_ngram`) — a lexical approximation, not semantic dedup, despite the class name and contract documentation.
- **Impact:** Semantic near-duplicates (paraphrases, translated variants, reworded sentences) are never caught in production configuration; token budget wasted on redundant evidence.
- **Recommended Fix:** Require an `IEmbeddingProvider` in the registry whenever `dedup_near_enabled=True`; fail loudly (or clearly log a degraded-mode warning) rather than silently substituting a much weaker algorithm.

### EO-02 — Near-duplicate detection is O(n²) and the documented batch-size safety valve doesn't fix the complexity
- **Severity:** High
- **Category:** Performance
- **Location:** `embedding_deduplicator.py::_near_dedup_embedding` / `_near_dedup_ngram` — nested `for i / for j in range(i+1, n)`; `dedup_near_batch_limit=200` only skips the *embedding API call*, the pairwise Jaccard loop still runs at full O(n²); `celery_offload_threshold=500` is configured but never referenced anywhere in code
- **Impact:** At 200–500 retrieved candidates (easily reached with multi-strategy retrieval + expansion), this becomes a latency cliff that can blow the orchestrator's own indicative 500ms budget.
- **Recommended Fix:** Block-by-`doc_id` before pairwise comparison, or use MinHash/LSH for approximate near-dup detection; implement or delete the dead Celery-offload config.

### EO-03 — Conflict detection runs *after* budget-based selection, breaking the specified "budget_drop" disclosure guarantee
- **Severity:** Critical
- **Category:** Reliability
- **Location:** `context_builder/pipeline.py::_build_inner` (L120–144) — order is `_select_under_budget` → dedup → **then** `detect(deduped)`; `_apply_conflict_resolutions` (L268–286)
- **Problem:** The spec's edge case explicitly requires that if one side of a contradiction is dropped for budget reasons, the surviving `Context.conflicts` must still record the group with `resolution="budget_drop"` — but a budget-dropped item is never seen by the detector, because detection runs only on the post-selection survivor set.
- **Impact:** This is a **safety-relevant regression**: the exact scenario the conflict-disclosure feature exists to protect against (one-sided evidence reaching the user because budget silently dropped the contradicting source) is the one case where disclosure cannot fire.
- **Recommended Fix:** Run conflict detection on the full pre-selection pack (or track omitted members explicitly), then select under budget with conflict-awareness, tagging `resolution="budget_drop"` whenever any group member is omitted.

### EO-04 — Conflict detector is a fragile heuristic prone to false positives
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `context_builder/conflict/entity_tag_detector.py::EntityTagConflictDetector` (L29–101) — groups by shared entity tag, then flags conflict if *any* distinct numbers appear near the tag within a ±100-char window; explicitly ignores its own `config` parameter (`_ = config`)
- **Impact:** Distinguishes "5mg vs 10mg dose" (real conflict) no better than "page 5 vs section 10" (noise) — numeric co-occurrence near a shared entity is not evidence of contradiction. Configured tolerance is dead code.
- **Recommended Fix:** Require the *same attribute type* (not just proximity) before flagging a conflict; honor configured numeric tolerance; expand the tiny hardcoded categorical-antonym list into pack config.

### EO-05 — Compressibility is scored against pre-fusion relevance, then fusion re-ranks everything, invalidating the score
- **Severity:** High
- **Category:** Architecture
- **Location:** `evidence_orchestrator/pipeline.py::orchestrate` (compress_flag stage precedes prioritize stage); `redundancy_scorer.py` uses `1 - relevance_score` at the point it runs; `fusion_prioritizer.py` subsequently overwrites `relevance_score`
- **Impact:** Compressibility flags reflect a ranking that no longer exists by the time Context Builder consumes them, so the "compress low-value, preserve high-value" policy can compress the wrong items.
- **Recommended Fix:** Reorder pipeline: prioritize (fuse) before scoring compressibility, or rescore compressibility after fusion.

### EO-06 — First over-budget compressible item can consume the entire remaining token budget
- **Severity:** High
- **Category:** Design
- **Location:** `context_builder/pipeline.py::_select_under_budget` (L236–252) passes `remaining = budget - budget_used` as the compression target for the *first* overflow item
- **Impact:** One mediocre item can be compressed into a summary that fills the entire leftover window, starving several smaller, higher-value items that would otherwise have fit.
- **Recommended Fix:** Cap each item's compression target to a fair share of remaining budget (or do a two-pass allocation: reserve slots for top-K low-compressibility items first, then fill the remainder).

### EO-07 — LLM-based compression is lossy, unmeasured, and fully serial
- **Severity:** High
- **Category:** Reliability / Performance
- **Location:** `context_builder/compression/llm_compressor.py::LLMContextCompressor.compress` (L33–62); invoked with a sequential `await` per item inside `_select_under_budget`
- **Problem:** No information-retention check exists before/after summarization; a new LLM client is constructed per call (no reuse/caching); overflow items are compressed one at a time, not in parallel.
- **Impact:** Necessary facts (dosages, caveats, exceptions) can be silently dropped by the summarizer with no detection; under the configured 30s context-build timeout, several sequential LLM round-trips can exceed budget and drop the entire context (`timeout=True` fallback discards *all* evidence, not just the slow item).
- **Recommended Fix:** Prefer extractive compression (retain highest-salience sentences by query/entity overlap) as the default; if abstractive LLM compression is used, gate acceptance behind a lightweight retention check (numeric/entity overlap) and parallelize with a concurrency limit and client reuse.

### EO-08 — Token counting defaults to a crude character÷4 approximation in production config
- **Severity:** High
- **Category:** Reliability
- **Location:** `fields/generic/evidence_orchestrator.yaml` / `context_builder.yaml` both set `token_counter: character`; `character_approximation.py` (`ceil(len(text)/4)`); Evidence Orchestrator's registry additionally **ignores** `config.token_counter` for the packaging stage even when a real counter is configured
- **Impact:** Silent budget miscalculation — CJK/code-heavy text is drastically undercounted (risking real LLM context overflow), English prose overcounted (wasting budget) — while every internal check reports "within budget."
- **Recommended Fix:** Default to a real tokenizer (tiktoken or the answer model's native encoding) whenever known; make the character approximation an explicit, logged fallback only; fix the registry to honor configured counters consistently.

### EO-09 — Fusion prioritization has a broken empty-entity case and a fabricated "recency" signal
- **Severity:** High
- **Category:** Design
- **Location:** `evidence_orchestrator/prioritization/fusion_prioritizer.py` — when `plan.entities` is empty, the entity-weight component is mathematically zeroed but the 0.6/0.3/0.1 weight split is never renormalized, permanently discarding 10–30% of achievable score mass; "recency" is computed from `chunk_index` (position within a document), not any real timestamp, because `SourceRef` has no timestamp field
- **Impact:** Systematic, silent score distortion on every entity-sparse query; "recency boost" is a fictitious signal that rewards later chunks in a file for no principled reason.
- **Recommended Fix:** Renormalize weights when entity signal is unavailable; either add real document timestamps upstream or remove the recency component entirely rather than fake it with document position.

### EO-10 — Citation lineage does not survive compression or expansion
- **Severity:** Medium
- **Category:** Design
- **Location:** `Citation` model has no character-span field; compression replaces `ContextBlock.text` while `citation_map` still points at the *original* full chunk; lineage expansion (`expansion/lineage_expander.py`) appends neighbor-chunk text without updating the citation's chunk-id scope
- **Impact:** "Click citation to see source" UX becomes misleading post-compression (cited text ≠ prompt text) and post-expansion (citation names one chunk while the block contains three); downstream faithfulness scoring compares against text the citation doesn't actually represent.
- **Recommended Fix:** Mark compressed blocks as non-verbatim explicitly; record `expanded_chunk_ids` alongside the primary citation.

---

## 8. Context Builder

*(Several Context Builder findings are cross-listed under Evidence Orchestration above — EO-03, EO-06, EO-07, EO-08, EO-10 — because the two modules' pipelines are tightly coupled at the point of failure.)*

### CB-01 — Stitching order can bury the most relevant evidence deep in the prompt
- **Severity:** Medium
- **Category:** Design
- **Location:** `context_builder/stitching/section_path_stitcher.py::_sort_key` (L12–40) sorts by `(doc_id lexicographic, section_path lexicographic, -relevance)`
- **Impact:** Document and section ordering is alphabetical, not relevance- or outline-driven; the single most relevant chunk can end up last in the prompt, subject to known LLM "lost in the middle" attention degradation, purely because its `doc_id` string sorts late.
- **Recommended Fix:** Primary sort by per-document max relevance (or explicit plan-provided document order), secondary by parsed hierarchical section path, tertiary by relevance — never raw string lexicographic order as the primary key.

### CB-02 — Token budget allocation is fixed reservation, not adaptive
- **Severity:** Medium
- **Category:** Design
- **Location:** `context_builder/budget/default_allocator.py` (L10–12) returns `window - system - question - output`, with `question` reserved as a static 200-token constant regardless of actual question length
- **Impact:** Short questions waste reserved budget; long questions silently steal from the evidence budget instead of triggering their own truncation path.
- **Recommended Fix:** Measure actual system+question token counts at build time; allocate the true remainder to evidence.

### CB-03 — Final-pass "safety net" dedup duplicates Evidence Orchestrator's algorithm rather than complementing it
- **Severity:** Medium
- **Category:** Maintainability
- **Location:** `context_builder/dedup/text_similarity_dedup.py` (0.85 threshold) vs `evidence_orchestrator/deduplication` (0.95 threshold) — both are the same char-ngram Jaccard family
- **Impact:** Two thresholds for "the same algorithm" invite drift and inconsistent duplicate decisions; capped at `final_dedup_max_pairs=2000` with no relevance pre-sort, so which duplicate survives is order-dependent, not quality-dependent.
- **Recommended Fix:** Extract one shared near-duplicate utility; sort candidates by relevance before capping pairwise comparisons so the *better* item is reliably kept.

---

## 9. Answer Generation

### AG-01 — Retrieved document text and user questions are concatenated into the LLM prompt with zero sanitization or isolation
- **Severity:** High
- **Category:** Security
- **Location:** `answer_generation/composition/default_composer.py::DefaultPromptComposer.compose` (L27–34) — `block.text` and `question` are string-concatenated into the user message with no delimiting, escaping, or instruction-isolation
- **Impact:** Classic indirect prompt injection: any document ingested into the corpus (which, per Finding S1/S2 below, can come from unauthenticated uploads) can contain text designed to override system instructions, exfiltrate other users' context, or suppress citations — and nothing in the composition layer defends against it.
- **Recommended Fix:** Wrap untrusted content (retrieved chunks, user query) in explicit data envelopes (XML/JSON with "treat as data, not instructions" framing); consider output-side filtering for instruction-like patterns in generated answers.

### AG-02 — Inline grounding checker only recognizes Title-Case multi-word phrases and fails open on any error
- **Severity:** Critical
- **Category:** Reliability
- **Location:** `answer_generation/grounding/entity_tag_checker.py::EntityTagGroundingChecker.check` (L64–103) — regex-based Title-Case entity extraction only; wraps its own logic in `try/except: return []` (silently reports "no ungrounded entities" on internal failure)
- **Problem:** This is, by design (per spec 013), a flag-only, non-blocking guard — but its detection surface is so narrow (numbers, single-token names, lowercase claims, and any claim shape other than "Capitalized Phrase" are invisible to it) that it catches almost nothing in a domain like pharmacy where the highest-risk hallucinations are numeric (doses, frequencies).
- **Impact:** A fabricated dosage number, a hallucinated single-word drug name, or any lowercase claim sails through both this checker and reaches the user, with only a metrics counter incremented — no block, no rewrite, no escalation.
- **Recommended Fix:** For high-risk domains (configurable via field pack), broaden detection to numeric claims and known-entity dictionaries, and add a policy tier that can fail closed (reject/regenerate) above a configurable flag-count threshold — "flag-only forever" is not an acceptable terminal state for a production safety control.

### AG-03 — Structured-output parsing has no repair/retry; truncated JSON becomes the literal user-facing answer
- **Severity:** High
- **Category:** Reliability
- **Location:** `answer_generation/parsing/json_output_parser.py::JsonOutputParser.parse` (L32–53) — on `JSONDecodeError`, the *entire raw string* (including stray braces/partial JSON) becomes `answer_text`; pipeline requests `response_mime_type="application/json"` but never sets `response_schema` (unlike `query_parser`, which does)
- **Impact:** Any truncated or malformed LLM response — token-limit cutoffs are common — ships broken JSON fragments directly to the user instead of a clean error or repaired answer.
- **Recommended Fix:** Add brace-extraction/JSON-repair before falling back to plain text; pass a strict `response_schema` wherever the provider supports it; on unrecoverable parse failure, return a structured `no_answer` result, not raw garbage.

### AG-04 — Citations are formatted, not verified
- **Severity:** High
- **Category:** Design
- **Location:** `answer_generation/citation/item_id_formatter.py::ItemIdCitationFormatter.format` (L14–49)
- **Problem:** The formatter resolves `[ei_<hex>]` markers to metadata but never checks that the cited chunk's text actually supports the adjacent claim.
- **Impact:** An LLM can cite a real, resolvable `item_id` next to a completely fabricated claim, and the UI will render it as a fully-grounded, clickable citation — the worst kind of hallucination because it *looks* trustworthy.
- **Recommended Fix:** Add a post-generation check (lexical overlap at minimum, NLI/entailment ideally) verifying each cited block supports its adjacent claim before formatting; strip or flag unsupported citations rather than rendering them as-is.

### AG-05 — Non-deterministic generation defaults undermine golden-test reproducibility
- **Severity:** High
- **Category:** Reliability
- **Location:** `answer_generation/config.py` default `temperature=0.3`; `stores/llm/LLMInterface.py` has no `seed` parameter anywhere in the interface
- **Impact:** Regenerating golden snapshots from a live pipeline run will drift run-to-run, making the offline evaluation suite (spec 014) unable to distinguish "real regression" from "temperature noise" if it were ever run against a live pipeline instead of hand-authored snapshots.
- **Recommended Fix:** Add a `seed` parameter to `LLMInterface`; use `temperature=0` + fixed seed for any evaluation/golden-recording profile.

### AG-06 — Answer Generation module is not reachable from any API route
- **Severity:** Critical
- **Category:** Architecture
- *(Instance of ARCH-01.)* `src/routes/` has zero imports of `answer_generation`; production still uses a hand-built prompt/parsing path inside `answer_service.py`.

---

## 10. Evaluation Platform (Answer Quality)

### AQ-01 — Faithfulness scorer defaults to a perfect score of 1.0 when it cannot extract any checkable spans
- **Severity:** Critical
- **Category:** Testing
- **Location:** `answer_quality/faithfulness/scorer.py::TextFaithfulnessScorer.score` — `total = max(len(spans), 1); score = 1.0 - (len(unsupported)/total)`
- **Problem:** If the answer contains no numbers, no Title-Case phrases, and no quotes (i.e., plain lowercase prose — one of the most common hallucination shapes), `spans=[]`, `unsupported=[]`, and the formula evaluates to a perfect `1.0`.
- **Impact:** A **fully fabricated** plain-sentence answer passes the faithfulness gate with a perfect score. This is not an edge case — it's a systematic blind spot that a mildly adversarial answer generator (or just an unlucky model completion) will hit routinely. This single bug makes the offline faithfulness metric unsafe to trust as a quality gate in its current form.
- **Recommended Fix:** When zero checkable spans exist for a non-empty answer, the score must be `N/A`/`unknown` (excluded from pass/fail, flagged for manual review) — never default to a perfect pass. Longer term, replace span-substring heuristics with sentence-level entailment (NLI) against cited context.

### AQ-02 — Completeness scoring is keyword-overlap and is gameable by padding
- **Severity:** High
- **Category:** Testing
- **Location:** `answer_quality/completeness/scorer.py::KeywordCompletenessScorer` — passes any facet whose tokens appear ≥50% anywhere in the answer, stopwords stripped
- **Impact:** Verbose, keyword-stuffed non-answers score as "complete"; correct paraphrases without matching surface tokens score as "incomplete" — the metric measures lexical overlap, not actual information coverage.
- **Recommended Fix:** Move to embedding-similarity or NLI-based facet coverage behind the same scorer interface; raise/parametrize the overlap threshold per field-pack criticality.

### AQ-03 — Faithfulness is measured against the entire retrieved context, not the chunks the answer actually cited
- **Severity:** Medium
- **Category:** Design
- **Location:** Spec FR-005 wording says "vs. cited chunks"; implementation (per research note R-03) checks against **all** `ordered_blocks[*].text`
- **Impact:** An answer can be scored "faithful" because *some* uncited block in the context happens to support the claim, even though the answer didn't cite it — inflating faithfulness relative to what the citation UI actually shows the user.
- **Recommended Fix:** Restrict the faithfulness corpus to blocks whose `item_id` intersects the answer's actual citation set.

### AQ-04 — Golden dataset has 3 fixtures, all single-hop pharmacy questions; spec requires ≥10 and no diversity criteria are met
- **Severity:** Critical
- **Category:** Testing
- **Location:** `tests/fixtures/answer_quality/generic_golden.yaml` (q001–q003 only); spec 014 success criterion SC-001 requires ≥10 questions, with plan-level language suggesting eventual scale to 10–100
- **Problem:** No unanswerable/no-answer cases, no injected contradictions, no multi-hop questions, no adversarial-hallucination cases, no citation-error cases, no non-pharmacy domain coverage. Snapshots even use placeholder evidence text (`"Text for doc-…"`) rather than realistic content.
- **Impact:** A green CI run on this dataset provides essentially no confidence that the pipeline handles the failure modes evaluation platforms exist to catch. Combined with AQ-01/AQ-02, the entire offline quality gate is currently more theater than safety net.
- **Recommended Fix:** Expand to ≥30–50 cases spanning: single-hop, multi-hop, unanswerable, contradictory-source, citation-error, and adversarial-hallucination categories, across at least two field packs (pharmacy + one other) before treating this gate as trustworthy.

### AQ-05 — No CI ever invokes the evaluation gate; `run_and_exit` has no caller
- **Severity:** Critical
- **Category:** Architecture / Reliability
- **Location:** `answer_quality/registry.py::AnswerQualityRegistry.run_and_exit` (returns process exit codes 0/1/2, designed for CI) — grep confirms zero callers anywhere in the repo outside its own tests; no `.github/workflows/`, no CI config of any kind exists in the repository
- **Impact:** Regardless of how good the scorers are, nothing currently stops a regressive change from merging — the "evaluation and gating layer" described in AGENTS.md gates nothing today.
- **Recommended Fix:** Add a CI workflow that runs `run_and_exit` on every PR and fails the build on nonzero exit; this is a near-zero-effort, high-value fix relative to everything else in this report.

### AQ-06 — Regression detection is a naive fixed-threshold diff with no statistical treatment and silently skips mismatched question sets
- **Severity:** Medium
- **Category:** Design
- **Location:** `answer_quality/regression/store.py::JsonRegressionStore.diff` — flags regression only if `abs(delta) >= 0.1`; questions present in only one of the two compared runs are silently skipped rather than flagged
- **Impact:** Small but real regressions under the 0.1 threshold accumulate invisibly; if the golden set changes between runs (a question added/removed), coverage gaps go unnoticed rather than erroring.
- **Recommended Fix:** Require identical question-ID sets between baseline and candidate runs (error on mismatch); consider smaller thresholds with confidence intervals as the dataset grows past the current 3-question toy size.

### AQ-07 — Coverage/faithfulness/completeness scorers are hardcoded classes with no config-driven selection
- **Severity:** Medium
- **Category:** Extensibility
- *(Instance of ARCH-05.)* `AnswerQualityRegistry` hardcodes `DocIdCoverageEvaluator`/`TextFaithfulnessScorer`/`KeywordCompletenessScorer`; swapping to a semantic scorer requires a code change, not a config change.

---

## 11. Observability

### OBS-01 — No distributed tracing; per-module trace objects are ephemeral and never correlated end-to-end
- **Severity:** High
- **Category:** Architecture
- **Location:** `retrieval_engine/tracing/tracer.py::RetrievalTracer` accumulates `RetrievalStepTrace` objects into the in-process `RetrievalResult.trace`; no OpenTelemetry/Jaeger/Tempo integration anywhere in the repo; planner uses plain `logging` with extras only
- **Impact:** Even if the SpecKit stack were wired into production (ARCH-01), there is currently no way to follow one request's `plan_id`/`trace_id` across planner → engine → orchestrator → context builder → answer generation in a queryable store — every debugging session would require log-scraping across five modules.
- **Recommended Fix:** Adopt OpenTelemetry spans with a request-scoped correlation ID propagated as baggage through every stage; export to a trace backend; sample in production, always-on in staging.

### OBS-02 — No cost/token-usage tracking anywhere in the metrics surface
- **Severity:** High
- **Category:** Reliability
- **Location:** `src/utils/metrics.py` — latency and count metrics exist for retrieval/generation/rerank/DI/context-builder/answer-generation stages; no `llm_tokens_total` or cost-estimate metric exists for any provider; Vertex gathers `usage_metadata` only into an internal diagnostics dict that isn't exported
- **Impact:** No way to budget, alert on, or even retroactively explain an LLM spend spike — a basic FinOps capability missing entirely.
- **Recommended Fix:** Emit `llm_tokens_total{provider,model,direction}` and derived cost-estimate metrics from every provider adapter, not just Vertex's internal diagnostics.

### OBS-03 — Metrics endpoint relies on an obscure path instead of real access control
- **Severity:** Medium
- **Category:** Security
- **Location:** `utils/metrics.py` (L143–146) — Prometheus endpoint is exposed at a randomized-looking path (`/TrhBVe_m5gg2522_esvVqS`) with no auth
- **Impact:** Security-through-obscurity; anyone who discovers the path (log leakage, browser history, proxy config) gets full metrics access including per-`project_id` label cardinality (a minor data-disclosure vector on top of the availability risk).
- **Recommended Fix:** Put metrics behind network-level restriction (internal-only ingress) or real auth; avoid high-cardinality identifying labels.

### OBS-04 — No application health/readiness endpoints
- **Severity:** High
- **Category:** Reliability
- **Location:** `src/routes/base.py` exposes only a static "app name/version" response at `/api/v1/`; the FastAPI service has no `healthcheck` in `docker-compose.yml` (unlike Postgres/RabbitMQ/Redis, which do)
- **Impact:** Orchestrators (k8s, compose, load balancers) cannot distinguish "process alive" from "DB/vectordb/broker reachable," meaning traffic can be routed to an instance that is up but non-functional, and rolling deploys have no reliable readiness gate.
- **Recommended Fix:** Add `/healthz` (liveness: process up) and `/readyz` (readiness: DB ping, vectordb ping, broker ping) endpoints; wire them into compose/k8s probes.

### OBS-05 — Planner diagnostics fields are declared but never populated
- **Severity:** Medium
- **Category:** Observability
- **Location:** `retrieval_planner/models.py::PlannerDiagnostics` — `intent_candidates`, `entity_resolution_trace`, `strategy_selection_trace` are always empty; only `clarification_trigger`/`limits_derivation`/`planning_latency_ms` are ever set
- **Impact:** The debugging metadata the spec calls for ("why did the planner choose these strategies") is structurally present but functionally hollow.
- **Recommended Fix:** Have each pipeline stage append a structured trace entry when diagnostics are enabled, rather than leaving the richest fields permanently empty.

---

## 12. Performance

### PERF-01 — Celery task setup recreates DB engines and provider clients on every task invocation
- **Severity:** High
- **Category:** Performance
- **Location:** `src/celery_runtime.py::get_setup_utils` (L26–89) — each call does `create_async_engine(pool_size=4, max_overflow=8)` plus fresh LLM/vectordb client construction; worker concurrency is set to 8 (`docker-compose.yml` L51)
- **Impact:** Every indexing task pays full connection/client bootstrap cost; under concurrent task load this produces connection storms against Postgres and repeated model-client initialization overhead — a direct throughput ceiling on ingestion.
- **Recommended Fix:** Initialize engines/clients once per worker process (`worker_process_init` signal) and reuse across tasks within that process.

### PERF-02 — Celery chord coordinator blocks a worker slot waiting on `.get()`
- **Severity:** High
- **Category:** Performance
- **Location:** `src/tasks/data_indexing.py::dispatch_index_data_content` (L329–341) — `chord(...)()` followed by a synchronous `chord_result.get(timeout=...)` inside the coordinating task
- **Impact:** Under load, coordinator tasks occupy a full concurrency slot for the entire duration of their fanned-out shards, which can starve/deadlock the worker pool and makes large ingestion jobs prone to timeout-triggered failure.
- **Recommended Fix:** Use a chord callback task instead of synchronously blocking on `.get()` inside a parent task.

### PERF-03 — O(n²) similarity computations appear in three independent places without shared mitigation
- **Severity:** High
- **Category:** Performance
- *(Consolidates EO-02 and CB-03.)* Evidence Orchestrator near-dedup, Context Builder final-pass dedup, and (to a lesser extent) redundancy scoring all run pairwise comparisons over the same class of candidate sets. None uses blocking, ANN, or LSH.
- **Recommended Fix:** Build one shared near-duplicate index utility (LSH/MinHash or ANN-backed) used by all three call sites instead of three independent O(n²) implementations.

### PERF-04 — Sequential, uncached LLM calls in the compression hot path
- **Severity:** High
- **Category:** Performance
- *(= EO-07.)* Per-item sequential `await compressor.compress(...)` with a fresh LLM client constructed per call.

### PERF-05 — No caching layer for embeddings/LLM calls outside a single in-process cache
- **Severity:** Medium
- **Category:** Performance
- **Location:** `EMBEDDING_GLOBAL_CACHE_*` config implies an in-process cache only; no distributed cache (Redis) for embeddings or LLM completions across API replicas
- **Impact:** Horizontally scaled API replicas each maintain independent caches, multiplying redundant embedding/LLM cost and preventing warm-cache benefits from being shared across the fleet.
- **Recommended Fix:** Move hot caches (query embeddings, repeated LLM completions with deterministic settings) to a shared Redis-backed cache.

### PERF-06 — API is effectively pinned to a single worker process due to local reranker/embedding state
- **Severity:** Medium
- **Category:** Scalability
- **Location:** `docker-compose.yml` runs the FastAPI service with `--workers 1`; local HuggingFace model cache and BGE reranker state live in-process
- **Impact:** Vertical scaling only; cannot horizontally scale the API tier without externalizing rerank/embedding compute into a dedicated service.
- **Recommended Fix:** Extract CPU-heavy rerank/embedding into a separate stateless service (or sidecar) callable by any number of API replicas.

---

## 13. Production Readiness

### SEC-01 — Authentication is a spoofable client-supplied header
- **Severity:** Critical
- **Category:** Security
- **Location:** `src/helpers/auth.py::get_current_user_id` — accepts any non-empty `X-User-Id` header as truth; frontend even defaults to `localStorage` value or the literal string `"demo-user"` (`src/frontend/js/chat.js`)
- **Impact:** Any client can impersonate any user by setting a header; there is no cryptographic identity verification anywhere in the request path.
- **Recommended Fix:** Replace with signed tokens (JWT/OIDC) validated server-side; never trust a client-supplied identity header as authentication.

### SEC-02 — Data and NLP routes (upload, process, index, search, answer) have no authentication or ownership checks at all
- **Severity:** Critical
- **Category:** Security
- **Location:** `src/routes/data.py`, `src/routes/nlp.py` — no `Depends(get_current_user_id)`, contrasted with `src/routes/projects.py` which does use it; `get_project_or_create_one` (`project_repository.py` L28–44) auto-creates a project row for any numeric ID with zero ownership validation
- **Impact:** Any unauthenticated caller can upload documents into any project, trigger indexing, search any project's content, and get answers grounded in any project's documents — a complete cross-tenant data exposure and a costly DoS/abuse vector (unbounded LLM/embedding spend). This is the single most severe finding in the entire audit.
- **Recommended Fix:** Require authenticated + authorized (project-membership-checked) access on every data/nlp endpoint before this system touches real user data; remove auto-create-on-access entirely — projects should only be created through an explicit, authorized flow.

### SEC-03 — Answer API returns the full assembled prompt and chat history to the client
- **Severity:** High
- **Category:** Security
- **Location:** `src/routes/nlp.py` (L201–208) response includes `full_prompt` and `chat_history` fields
- **Impact:** Leaks the entire retrieved-document context (not just the answer) to the client, and provides an attacker a direct view into prompt structure — useful reconnaissance for prompt-injection attacks and a straightforward document-content exfiltration path that bypasses any UI-level redaction.
- **Recommended Fix:** Return only the answer + structured citations by default; gate debug fields behind admin-only auth or a feature flag disabled in production.

### SEC-04 — File upload validation trusts client-supplied MIME type; no content sniffing or resource-exhaustion limits
- **Severity:** High
- **Category:** Security
- **Location:** `src/services/data_service.py::validate_uploaded_file` (L14–22) checks `content_type` (client-controlled) and size only; no magic-byte verification, no page-count/pixel-count caps before handing files to OCR/Docling
- **Impact:** A relabeled malicious file reaches parsers/OCR; a crafted PDF (huge page count, decompression bomb) can exhaust worker CPU/memory — an easy DoS vector, compounded by SEC-02's lack of auth.
- **Recommended Fix:** Validate actual file content via magic-byte sniffing (e.g., `python-magic`), enforce hard page/pixel/size ceilings before OCR, and consider sandboxing/quarantining untrusted parse jobs.

### SEC-05 — No system-wide, single-tenant data model despite multi-user database schema
- **Severity:** High
- **Category:** Architecture
- **Location:** `models/db_schemes/algorag/schemes/*` — `Project`, `Asset`, `DataChunk`, `ChatMessage` have no `tenant_id`/`org_id`; isolation, where it exists at all, is via optional `ProjectUser` YAML-synced assignments that data/NLP routes don't even check (SEC-02)
- **Impact:** Cannot safely host multiple customer organizations on one deployment; "multi-user" today means "multiple people can see each other's data unless the frontend happens to filter it."
- **Recommended Fix:** Add an explicit `tenant_id`/`org_id` column enforced at the repository layer (not just the route layer) on every table that stores customer data.

### SEC-06 — BM25 tsquery construction is vulnerable to operator injection
- **Severity:** Medium
- **Category:** Security
- **Location:** `stores/vectordb/providers/pgvector/search.py::_build_tsquery` (L62–68) — joins raw tokens with `:*` directly into `to_tsquery`
- **Impact:** Query tokens containing tsquery operators (`&`, `|`, `!`, parentheses) can alter query semantics or trigger errors (partially masked by a catch-all `except: return []`).
- **Recommended Fix:** Use `websearch_to_tsquery`/`plainto_tsquery`, or escape operator characters explicitly before building the query.

### PROD-01 — Idempotency is task-argument hashing, not content-based deduplication, and indexing doesn't use it at all
- **Severity:** High
- **Category:** Reliability
- **Location:** `src/utils/idempotency_manager.py` used in `tasks/file_processing.py`; **not** used in `tasks/data_indexing.py`; `build_asset_fingerprint` (`project_assets.py` L4–15) hashes `asset_id:asset_name` only, not file bytes
- **Impact:** Replacing a file's content while keeping the same name can be treated as "already processed" (stale data served); indexing retries can double-insert vectors since indexing has no idempotency guard at all.
- **Recommended Fix:** Fingerprint on content hash (SHA-256 of bytes), not name; apply the idempotency manager to indexing; add a DB unique constraint on `(collection, chunk_id)`.

### PROD-02 — Retry strategy has no dead-letter queue or exponential backoff
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `tasks/data_indexing.py` — `autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 60}` (fixed delay, catches all exceptions equally)
- **Impact:** Transient rate-limit errors and permanent poison-message errors are retried identically; after 3 failures, tasks simply vanish into the result backend with no operable failure queue.
- **Recommended Fix:** Exponential backoff with jitter; distinguish retryable vs. terminal exception types; route exhausted-retry tasks to a dead-letter queue with alerting.

### PROD-03 — VectorDB "abstraction" is theoretical — pgvector-shaped, with the only alternative (Qdrant) missing feature parity
- **Severity:** High
- **Category:** Architecture
- **Location:** `stores/vectordb/VectorDBInterface.py` (minimal: connect/CRUD/`search_by_vector`); `PGVectorProvider` adds `search_by_text*`, `*_filtered`, `*_scoped`, `get_indexed_chunk_ids` not on the interface; `rag_service.py` gates hybrid features behind `hasattr(self.vectordb_client, "search_by_text")`; Qdrant service is commented out in `docker-compose.yml`
- **Impact:** Swapping the vector backend silently degrades hybrid retrieval instead of failing to build — the "pluggable vector store" promise is not actually enforced by the type system.
- **Recommended Fix:** Expand `VectorDBInterface` to include every capability the retrieval layer actually depends on; implement Qdrant to parity or explicitly mark it unsupported and remove `hasattr`-based feature detection.

### PROD-04 — Startup does not validate that configured LLM/embedding backends have required credentials
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `src/helpers/config.py::Settings` — provider API keys are `Optional[str] = None`; no startup check that the *selected* `GENERATION_BACKEND`/`EMBEDDING_BACKEND` has its credentials present
- **Impact:** App reports healthy at startup and fails only on the first real request/task — a "false green" deploy signal.
- **Recommended Fix:** Validate required credentials for the actively-configured backends at startup; fail fast rather than on first use.

### PROD-05 — Only one Alembic migration exists; runtime DDL (index creation) happens at app startup instead
- **Severity:** Medium
- **Category:** Reliability
- **Location:** `models/db_schemes/algorag/alembic/versions/115ff82e229f_init.py` (sole revision); `helpers/db_indexes.py` creates GIN indexes at startup
- **Impact:** Schema history isn't reconstructable from migrations alone; environments can silently drift depending on whether startup DDL ran; rollback stories are unclear.
- **Recommended Fix:** Every schema/index change should be a tracked Alembic revision; startup DDL should be reserved for genuinely dynamic per-tenant objects only, with logging/alerting when it runs.

### PROD-06 — No circuit breakers on external LLM/vectordb calls
- **Severity:** High
- **Category:** Reliability
- **Location:** No unified timeout/circuit-breaker wrapper found around OpenAI/Vertex/Cohere generate calls or vectordb queries (only partial retry/backoff config for Vertex embeddings specifically)
- **Impact:** A hanging or degraded upstream LLM provider can cascade into thread/event-loop exhaustion and task pileup across the whole system, with no automatic isolation.
- **Recommended Fix:** Wrap every external call with a consistent timeout + circuit-breaker policy (e.g., `tenacity` + a breaker library); apply bulkhead isolation so LLM slowness can't starve DB-bound work or vice versa.

---

## 14. Testing

### TEST-01 — No CI pipeline runs any test on any pull request
- **Severity:** Critical
- **Category:** Testing
- **Location:** No `.github/workflows/`, no `azure-pipelines*`, no `tox.ini`, no root pytest config of any kind found in the repository
- **Impact:** Every other testing investment in this codebase (hundreds of unit tests, golden fixtures, benchmarks) provides **zero** protection against regressions merging to the main branch, because nothing runs them automatically. This is arguably as severe as ARCH-01 — a large, well-tested codebase with no enforcement mechanism is only marginally better than an untested one.
- **Recommended Fix:** Add a GitHub Actions workflow (or equivalent) that installs dependencies and runs `pytest` on every push/PR, failing the build on any non-zero exit; this is close to a one-day fix with an outsized risk reduction.

### TEST-02 — No genuine end-to-end test exists; every "*_e2e.py" file is a single-module pipeline test with mocks
- **Severity:** Critical
- **Category:** Testing
- **Location:** `tests/integration/test_{answer_generation,retrieval_engine,evidence_orchestrator,context_builder,knowledge}_e2e.py` — all use `MockLLM`, mock retrievers, or synthetic packs; none exercises the real chain from document upload through DI → chunking → parsing → planning → retrieval → orchestration → context → generation → answer
- **Impact:** Cross-stage integration bugs (schema drift, ID-prefix mismatches, citation_map incompatibilities) are invisible to the test suite by construction; combined with ARCH-01 (production doesn't even use most of these modules), the suite tests a pipeline shape that doesn't exist in production.
- **Recommended Fix:** Build one true end-to-end test using a real (test) Postgres/pgvector instance and either a recorded/VCR'd LLM or a cheap real model call, driving the actual production entrypoint, not module-level pipeline objects.

### TEST-03 — Query parser (the one production-wired module) has zero tests
- **Severity:** Critical
- **Category:** Testing
- *(= QP-04.)* Highest-risk, actually-live component has no regression coverage at all, despite spec tasks marked complete.

### TEST-04 — No contract tests verifying schema compatibility across module boundaries
- **Severity:** High
- **Category:** Testing
- **Location:** Each module tests its own schema version in isolation (`schema_version == "1.0.0"` assertions); no test constructs a real `EvidencePack` and feeds it through Context Builder, or a real `Context` through Answer Generation
- **Impact:** A field rename or version bump in one module can silently break its consumer with no test catching it before production (which, again, currently doesn't even use this chain — see ARCH-01 — but will once integrated).
- **Recommended Fix:** Add `tests/contract/` round-tripping real (not hand-mocked) objects through each stage boundary.

### TEST-05 — No pytest configuration, markers, or dependency-pinning discipline
- **Severity:** High
- **Category:** Maintainability
- **Location:** No `pyproject.toml`/`pytest.ini`; no `unit`/`integration`/`slow`/`requires_db` markers anywhere; `src/requirements.txt` mixes pinned (`==`) and unpinned (`>=`) dependencies; `pytest-benchmark` is used via `importorskip` but absent from requirements
- **Impact:** Cannot selectively run fast tests in CI vs. slow/external-dependency tests in a nightly job; dependency drift risk from unpinned packages; benchmark-gated tests silently no-op if the optional package isn't installed.
- **Recommended Fix:** Add `pyproject.toml` with test markers and `addopts`; pin all direct dependencies (ideally via a lockfile); declare `pytest-benchmark` as an explicit extras group.

### TEST-06 — Golden/planner test suites bypass the exact component they claim to validate
- **Severity:** Medium
- **Category:** Testing
- **Location:** `tests/integration/test_retrieval_planner_golden.py::_parse` hand-constructs `ParseResult`/`QueryPlan` objects directly, never invoking the real `query_parser`
- **Impact:** The planner's golden suite can stay green while the actual LLM-parsing layer regresses catastrophically — a false sense of end-to-end confidence.
- **Recommended Fix:** Add a second golden variant that starts from raw query strings and runs through the real parser (with a recorded/mocked LLM response), not a hand-built plan object.

### TEST-07 — Evaluation-relevant adversarial cases are entirely absent
- **Severity:** High
- **Category:** Testing
- *(= AQ-04, restated from a pure test-coverage lens.)* No test anywhere asserts that a hallucinated plain-sentence answer *fails* faithfulness (it currently wouldn't, per AQ-01) or that a keyword-stuffed non-answer *fails* completeness (it currently wouldn't, per AQ-02). The scorer bugs are undetected precisely because no test tries to break them.

---

## 15. Future Evolution Readiness

| Capability | Current readiness | Evidence | What's actually needed |
|---|---|---|---|
| **Multimodal documents / images** | Not ready | `DocumentModel` has no `blob_ref`/`media_type`; `figure-placeholder` type exists but no parser ever emits it (DI-07) | Extend `StructuralElement` with media references; add an image/DOCX/HTML parser |
| **OCR** | Partially ready, narrow | Docling used only as page-image → text OCR (`utils/docling_ocr.py`), not full layout extraction (DI-06) | Use full layout-aware Docling pipeline; preserve bounding boxes, not just flattened text |
| **Tables** | Weak | Whitespace-heuristic table detection in PDF (DI-06); table-row grouping structurally broken (DI-08); XLSX loads unbounded into memory (DI-02); table `fields` are flat untyped dicts (no merged-cell/nested-header support) | Real layout-based table extraction with typed schema; fix table-row grouping; streaming XLSX ingestion |
| **Graphs / knowledge graph reasoning** | Not ready | Graph representation is a stub (KR-04); graph retriever isn't real traversal (RET-02); relationship discoverer only emits structural edges (KR-02); no cross-document entity resolution (KR-03) | Real traversal-capable graph store; semantic relationship discovery; corpus-level entity resolution — all currently missing, not just immature |
| **Cross-document reasoning** | Not ready | Knowledge extraction is strictly per-asset (KR-03); no consumer of knowledge packages exists at all (ARCH-06); retrieval has no multi-document synthesis strategy beyond independent chunk retrieval | Requires the knowledge layer to actually be wired in, plus an explicit cross-document synthesis strategy in the planner |
| **Agentic retrieval** | Not architected | Planner produces one static plan; no iterative "retrieve → evaluate → refine → retrieve again" loop exists anywhere; clarification is a single-shot flag (PLAN-02), not a multi-turn negotiation | Would require a fundamentally different orchestration loop above today's single-pass planner→engine→answer pipeline |
| **MCP integration** | Not present | No MCP server/client code found anywhere in `src/` | Would be a net-new integration layer; today's tool surface is a closed FastAPI app, not tool-callable |
| **Distributed indexing** | Partial | Celery-based sharded indexing exists (`data_indexing.py`) but the coordinator blocks on `chord().get()` (PERF-02) and per-task engine/client recreation limits throughput (PERF-01) | Fix the two performance findings before this can be called "distributed" rather than "parallelized-but-serially-bottlenecked" |
| **Incremental indexing** | Partial | Chunk-ID-based skip-if-already-indexed exists when `do_reset != 1`; but idempotency is not content-hash based (PROD-01), so content changes under an unchanged filename won't be detected | Content-hash-based change detection is required for genuine incremental indexing |
| **Streaming ingestion** | Not ready | All parsers are batch, load-to-memory, synchronous (DI-02); no event-driven per-document ingestion API; indexing is triggered by explicit "process" calls, not a continuous feed | Requires streaming parsers plus an event-driven ingestion API, not just batch Celery tasks |
| **Multi-tenant deployments** | Not ready | No `tenant_id`/`org_id` in schema (SEC-05); routes bypass ownership checks entirely (SEC-02); per-project dynamic Postgres tables (PROD-05/P5) scale poorly with tenant count | This is a ground-up data-model and authorization change, not a config flag |
| **Billion-scale retrieval** | Not ready | Unbounded in-memory candidate fan-out with no filter/limit pushdown to stores (RET-07); O(n²) dedup/similarity in three places (PERF-03); one Postgres table per project collection (PROD-05); no ANN index tuning strategy beyond a deferred HNSW threshold | Needs filter pushdown, ANN-backed near-dup detection, and a data-partitioning strategy designed for scale, not organically grown from a single-tenant pgvector setup |

**Bottom line on future evolution:** the codebase is not "one increment away" from any of these capabilities — most require the *current* architecture's unresolved foundational gaps (ARCH-01's integration gap, the knowledge layer being orphaned, unbounded in-memory processing, single-tenant data model) to be fixed first. Building multimodal/graph/agentic features on top of the current foundation would compound the existing dual-stack problem into a triple- or quadruple-stack problem.

---

## Scores

| Dimension | Score | Justification |
|---|---|---|
| **1. Architecture Score** | **3/10** | Individual modules show genuinely good Clean Architecture instincts (interfaces, registries, Pydantic contracts, read-only dependency boundaries in answer_quality). The score is this low because the system-level architecture — the thing that actually matters — is two disconnected stacks (ARCH-01), with the more sophisticated one (specs 009–014) entirely unused in production, plus a genuinely orphaned module (knowledge representation, ARCH-06) and multiple dependency-direction violations (ARCH-04) even within "core." |
| **2. Production Readiness Score** | **2/10** | Unauthenticated data/NLP endpoints with auto-created projects (SEC-02) and spoofable identity (SEC-01) are disqualifying findings on their own for any real deployment. No CI (TEST-01), no health checks (OBS-04), no circuit breakers (PROD-06), theoretical vector-store pluggability (PROD-03), and idempotency gaps in the core ingestion path (PROD-01) compound this. This system is not safe to expose to real users or real documents today. |
| **3. Scalability Score** | **3/10** | Multiple O(n²) algorithms without blocking/ANN mitigation (PERF-03), unbounded in-memory document parsing (DI-02), no filter/limit pushdown to retrieval backends (RET-07), per-task connection/client recreation (PERF-01), a chord-blocking coordinator (PERF-02), single-worker API pinning (PERF-06), and no multi-tenant data model (SEC-05) mean this architecture has a low, not-yet-identified ceiling well short of "millions of chunks," let alone billion-scale. |
| **4. Maintainability Score** | **4/10** | Three parallel chunking pipelines (DI-01), two parallel retrieval stacks (ARCH-01/RET-08), two dedup implementations with different thresholds (CB-03), duplicate type definitions (ARCH-03), and registries that don't actually register anything dynamically (ARCH-05) all multiply the cost of every future change. Individual module code quality is often good in isolation — the debt is structural duplication and unclear ownership between old/new code paths, not sloppy code per se. |
| **5. Extensibility Score** | **4/10** | The field-registry (YAML pack) pattern is a genuinely good idea and works cleanly for prompt/threshold tuning (spec 002 pattern honored in answer_quality, evidence_orchestrator, context_builder). It breaks down exactly where it matters most: adding a document format touches 3–4 files (DI-10), adding a knowledge-unit type requires core code edits (KR-07), pharmacy vocabulary is hardcoded into "generic" parsing fallbacks (QP-01/ARCH-02) rather than being pack-driven. The pattern exists but isn't uniformly enforced. |
| **6. Code Quality Score** | **5/10** | Per-file code quality (typing, Pydantic models, docstrings, test coverage of individual functions) is above average for this class of project. The score is pulled down by correctness bugs that unit tests should have caught but didn't (faithfulness scorer defaulting to 1.0 on empty spans — AQ-01; table-row grouping unconditionally disabled — DI-08; dead batching code that's just `pass` — DI-02), and by config values that are silently ignored by the code that's supposed to read them (EO registry ignoring `config.token_counter`, `celery_offload_threshold` never referenced). |
| **7. NotebookLM Architecture Alignment** | **3/10** | NotebookLM-class systems are defined by tight source-grounded citation guarantees, real multi-document synthesis, and a coherent single retrieval pipeline the whole product runs on. This codebase has the *pieces* of that vision scattered across an unused SpecKit stack (planner, orchestrator, context builder, offline evaluation are all genuinely NotebookLM-shaped ideas) but none of it is connected to what a user actually experiences, citation verification is formatting-only (AG-04), and cross-document reasoning doesn't exist (see §15). The alignment is aspirational in the specs and absent in the running system. |

---

## Prioritized Roadmap

### P0 — Must fix before any production exposure
1. **SEC-02 / SEC-01** — Add real authentication and per-project authorization to every data/NLP route; remove auto-create-on-access; replace spoofable `X-User-Id` with signed tokens.
2. **TEST-01** — Stand up CI that runs the existing test suite on every PR. (Near-zero effort, prevents further silent regressions while everything else below is being fixed.)
3. **SEC-03** — Stop returning `full_prompt`/`chat_history` to API clients.
4. **AQ-01** — Fix the faithfulness scorer's empty-span-defaults-to-1.0 bug; it currently lets fully hallucinated answers pass the one automated safety gate this platform has.
5. **DI-02** — Fix or remove the dead XLSX batching code before any large-file ingestion is trusted; this is a live OOM risk today.
6. **DI-08** — Fix table-row grouping (unconditionally disabled), since tabular data is disproportionately high-value in business documents.
7. **AG-02** — Do not treat "flag-only, fail-open" grounding as an acceptable terminal state for a system handling pharmacy/legal content; add a fail-closed policy tier for high-risk fields.
8. **PROD-01** — Move ingestion idempotency to content-hash based, and apply it to the indexing task (currently unguarded).
9. **SEC-04** — Add real content-type verification and resource limits to file uploads before OCR/parsing.

### P1 — Strongly recommended (do before scaling users or documents)
1. **ARCH-01** — Commit to and execute the Integration Epic: wire specs 009–014 into the production answer path, or formally deprecate them. This is the highest-leverage architectural decision in the roadmap — it determines whether the next 12 months of engineering on this platform compounds or fragments further.
2. **TEST-02 / TEST-04** — Build one true end-to-end test (real DB, recorded LLM) and cross-module contract tests, ideally as part of the Integration Epic above.
3. **QP-01 / ARCH-02** — Remove hardcoded pharmacy vocabulary/fallback logic from "generic" core modules.
4. **EO-03** — Fix conflict detection running after budget selection; this breaks the specific safety guarantee (disclosing dropped contradictory evidence) the feature exists for.
5. **RET-01 / RET-03** — Make retrievers fail loudly when misconfigured (no store) instead of silently returning empty results; unify strategy-name vocabulary between planner and engine.
6. **EO-08** — Fix default token counting (character approximation) before trusting any budget-fits check in production.
7. **AQ-04 / AQ-05** — Expand the golden dataset to ≥30 cases with adversarial/multi-hop/unanswerable coverage, and wire `run_and_exit` into CI so it actually gates something.
8. **QP-04 / TEST-03** — Restore query parser tests; this is the one production-wired module with zero regression coverage.
9. **SEC-05** — Add tenant/org isolation to the data model before any multi-customer deployment is considered.
10. **PROD-06** — Add circuit breakers/timeouts around all external LLM/vectordb calls.
11. **OBS-04** — Add real health/readiness endpoints.
12. **PERF-01 / PERF-02** — Fix per-task Celery client/engine recreation and the chord-blocking coordinator before scaling ingestion volume.

### P2 — Nice improvements
1. **DI-06** — Move PDF parsing from whitespace heuristics to a real layout-aware parser.
2. **AG-03 / AG-04** — Add JSON repair/retry to answer parsing; add claim-to-citation verification instead of formatting-only citations.
3. **AQ-02** — Replace keyword-overlap completeness scoring with embedding/NLI-based facet coverage.
4. **CB-01** — Fix stitching order so relevance, not alphabetical `doc_id`, drives primacy in the prompt.
5. **RET-04** — Bridge the legacy rerank/expansion implementations into the SpecKit engine so a future cutover doesn't regress quality.
6. **OBS-01 / OBS-02** — Add OpenTelemetry tracing and LLM cost/token metrics.
7. **ARCH-05** — Make registries genuinely config-driven instead of hardcoded factories.
8. **PROD-03** — Expand `VectorDBInterface` to match what retrieval actually needs, or drop the pretense of pgvector/Qdrant interchangeability.
9. **PERF-05 / PERF-06** — Externalize embedding/rerank compute so the API tier can scale horizontally; move caching to a shared store.

### P3 — Long-term / future-evolution ideas
1. **Knowledge graph productization** (KR-02/KR-03/KR-04) — implement real semantic relationship discovery, cross-document entity resolution, and a real graph-traversal store, only after ARCH-06 gives the module an actual consumer.
2. **Multimodal ingestion** — extend `DocumentModel` with media references; add image/DOCX/HTML parsers; real table schema extraction with merged-cell/nested-header support.
3. **Agentic / iterative retrieval** — an orchestration loop above today's single-pass planner→engine→answer pipeline, supporting retrieve→evaluate→refine cycles and true multi-turn clarification.
4. **MCP tool-callable surface** — expose retrieval/answer capabilities as MCP tools for external agent consumption.
5. **Billion-scale retrieval architecture** — data-partitioning strategy (beyond one-Postgres-table-per-project), ANN-tuned vector indexing, and filter-pushdown-first retriever design, designed rather than organically extended from the current single-tenant pgvector setup.
6. **True streaming/event-driven ingestion** — replace batch-only Celery processing with a continuous ingestion pipeline supporting high-volume, always-on document feeds.

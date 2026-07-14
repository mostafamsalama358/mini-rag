# Implementation Plan: Knowledge Representation

**Branch**: `008-knowledge-representation` | **Date**: 2026-07-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-knowledge-representation/spec.md`

---

## Summary

Introduce a **Knowledge Representation** stage that transforms a validated `ChunkSet`
(output of `007-intelligent-chunking-engine`) into an immutable, representation-agnostic
**Knowledge Package** composed of **Knowledge Units** and **Knowledge Relationships**,
each carrying a complete **EvidenceReference** chain back to the source Chunk, Structural
Element, Document Model, and original document.

The stage is strategy-based across four pluggable components: `KnowledgeUnitExtractor`,
`KnowledgeNormalizer`, `RelationshipDiscoverer` (two-stage sub-pipeline), and
`KnowledgeRepresentationStrategy`. The default implementations for all three pipeline
strategies are deterministic and rule-based, requiring no LLM inference, embeddings,
or external network calls. Immutability is enforced via Pydantic v2 frozen models.

---

## Technical Context

**Language/Version**: Python 3.13 (constitution-mandated)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x (async), Pydantic v2, Celery

**Storage**: PostgreSQL + pgvector (primary); Knowledge Packages serialized to JSON
and stored in the asset file system or a new `knowledge_packages` DB table (repository
pattern, consistent with existing `chunk_repository.py`).

**Testing**: pytest + pytest-asyncio; `tests/unit/core/knowledge/` + `tests/integration/`

**Target Platform**: Linux server, Docker (same as existing platform)

**Project Type**: Internal RAG platform pipeline module

**Performance Goals**:
- End-to-end KR processing time ≤ 2× chunking stage wall time for a 50-chunk fixture
  ChunkSet on the same host (SC-008 latency budget). Default O(n) structural strategies
  make this feasible; the relationship discovery candidate step is O(n) with
  structural constraints.
- No LLM or network calls in any default strategy (FR-022, FR-023b, SC-007).

**Constraints**:
- No LLM inference, embeddings, vector store calls, or graph DB calls in core pipeline
  (FR-001, FR-003, SC-007).
- Knowledge Units, Relationships, and Knowledge Package are immutable once published
  (FR-008a, FR-009a, FR-017a) — enforced by `model_config = ConfigDict(frozen=True)`.
- Full traceability chain: every EvidenceReference must carry all four levels
  (Chunk id → Structural Element id → Document Model id → asset id) (FR-014).
- Celery-compatible for CPU-intensive workloads (NFR-002, Constitution X).

**Scale/Scope**: One ChunkSet per document → one KnowledgePackage per document;
per-asset invocation via Celery task (same pattern as `tasks/file_processing.py`).

---

## Constitution Check

Reference: `.specify/memory/constitution.md` (v1.0.0)

| Gate | Requirement | Pass? |
|------|-------------|-------|
| G1 Clean Architecture | KR domain models + interfaces in `src/core/knowledge/`; orchestration in `src/services/` or `src/tasks/`; no inward imports | ✅ |
| G2 Feature-First | All KR code co-located in `src/core/knowledge/`; tests co-located in `tests/unit/core/knowledge/` | ✅ |
| G3 SOLID / Plugins | Four pluggable interfaces (`KnowledgeUnitExtractor`, `KnowledgeNormalizer`, `RelationshipDiscoverer`, `KnowledgeRepresentationStrategy`); all wired via factory/registry | ✅ |
| G4 Async + Types | Celery worker for CPU work; Pydantic frozen models throughout; full type hints | ✅ |
| G5 RAG Pipeline | Pre-retrieval stage; EvidenceReferences enable production-grade citations (FR-014, Constitution VI.4) | ✅ |
| G6 Testing | Unit tests per pipeline stage; integration test for end-to-end KR run; SC tests in integration suite | ✅ |
| G7 Observability | Structured logging at extraction, normalization, discovery, assembly, validation boundaries (NFR-007) | ✅ |
| G8 Security | No new secrets in core; optional NLP API credentials via env vars per Constitution IX | ✅ |
| G9 Performance | Long KR runs in Celery workers; default strategies are O(n) so no batching needed at MVP | ✅ |
| G10 Stack | Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, Docker — no deviations | ✅ |

*All gates pass. No complexity justification required.*

---

## Project Structure

### Documentation (this feature)

```text
specs/008-knowledge-representation/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/           ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code

```text
src/core/knowledge/
├── __init__.py
├── models.py                  # KnowledgeUnit, KnowledgeRelationship, EvidenceReference,
│                              # RelationshipCandidate, KnowledgePackage,
│                              # KnowledgeValidationReport, KnowledgeStatistics,
│                              # KnowledgePackageMetadata, KnowledgeUnitType,
│                              # KnowledgeRelationshipType, ValidationRuleResult
├── interfaces.py              # KnowledgeUnitExtractor (ABC), KnowledgeNormalizer (ABC),
│                              # RelationshipDiscoverer (ABC),
│                              # KnowledgeRepresentationStrategy (Protocol)
├── pipeline.py                # KnowledgeRepresentationPipeline (orchestrator)
├── registry.py                # Extractor / Normalizer / Discoverer / RepStrategy registries
├── errors.py                  # KnowledgeRepresentationError, EvidenceIntegrityError, etc.
├── extractors/
│   ├── __init__.py
│   └── structural.py          # StructuralKnowledgeUnitExtractor (default, deterministic)
├── normalizers/
│   ├── __init__.py
│   └── rule_based.py          # RuleBasedKnowledgeNormalizer (default, deterministic)
├── discovery/
│   ├── __init__.py
│   ├── structural.py          # StructuralRelationshipDiscoverer (default, deterministic)
│   └── validator.py           # RelationshipCandidateValidator (sub-stage 2)
├── assembly.py                # KnowledgePackageAssembler
├── validation.py              # KnowledgeValidator + named quality rules
└── representation/
    ├── __init__.py
    └── base.py                # Re-export of KnowledgeRepresentationStrategy; no-op example

src/tasks/knowledge_representation.py  # Celery task: run_knowledge_representation(asset_id, ...)

tests/unit/core/knowledge/
├── conftest.py                # Fixture ChunkSets (5 semantic forms, alias pairs, malformed)
├── test_models.py             # Immutability, ID stability, field validation
├── test_structural_extractor.py
├── test_rule_based_normalizer.py
├── test_structural_discoverer.py
├── test_assembler.py
└── test_validator.py

tests/integration/
└── test_knowledge_pipeline_e2e.py   # Full ChunkSet → KnowledgePackage end-to-end
```

---

## Complexity Tracking

No Constitution Check violations. No complexity justifications required.

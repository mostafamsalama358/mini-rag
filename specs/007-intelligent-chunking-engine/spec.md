# Feature Specification: Intelligent Chunking Engine

**Feature Branch**: `007-intelligent-chunking-engine`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "Design an Intelligent Chunking stage for AlgoRAG from first principles.
Replace today's token-limit / simple-structural-heuristic chunking with semantic chunking driven
entirely by the Canonical Document Model produced by AI Document Intelligence (`006`). Chunking
must operate on document structure, never on raw text, and must preserve meaning over token
utilization: keep logical sections intact, produce complete semantic units, and support every
document type through a generic, strategy-based architecture with zero domain-specific logic.
The engine must support hierarchical/section/heading/table/list/code-block/quote/figure-aware
chunking, parent/child hierarchy, previous/next relationships, stable chunk identities, chunk
lineage, and source traceability — while remaining deterministic, reproducible, and swappable
without changing downstream indexing/retrieval/storage contracts. Output becomes the canonical
input for a future Knowledge Representation stage. Embeddings, entity/relation extraction,
retrieval, ranking, planning, and answer generation are out of scope."

## Executive Summary

The ingestion pipeline's chunking stage SHALL be replaced with an **Intelligent Chunking Engine**
that consumes only the **Canonical Document Model** (`DocumentModel` / `StructuralElement`,
produced by `006-document-intelligence-pipeline`) and never touches raw PDF, DOCX, HTML, or
Markdown content directly. Where today's `map_elements_to_chunks` heuristic groups adjacent
same-type elements up to a character budget and blindly slices anything oversized, the new engine
decides chunk boundaries through an explicit **Boundary Decision Pipeline**: every candidate
boundary between adjacent structural elements is analyzed by a **Semantic Boundary Evaluator**
across multiple independent, inspectable signals (hierarchy, heading, and section continuity;
structural compatibility; lexical continuity; table, list, code, and quote integrity; layout
continuity; size budget) — exposed as an explicit **Boundary Features** entity — and then resolved
by a separately swappable **Boundary Decision Policy** that emits an explicit **Boundary Decision**
— `decision` (merge or split), `applied_rule`, the specific `triggered_features` that drove it, and
a `rationale` — never a probabilistic confidence score, and never a single opaque "coherence
score". A dedicated, **stateful Chunk Builder** is the only component that turns those decisions
into actual Chunk objects: it incrementally opens, appends to, and closes each chunk before
assigning identity and relationships, and is the sole owner of any in-progress chunk's state; the
Decision Policy itself never constructs or mutates a chunk. This treats "preserve a complete
semantic unit" as the primary objective and "fit the token/character budget" as a secondary,
last-resort constraint.

The engine is **strategy-based**: boundary-detection, merge, and split behavior live behind one
swappable interface so new chunking approaches can be added without touching indexing, retrieval,
or chunk storage. Every produced chunk carries a **stable, deterministic identity**, **parent/child
hierarchy**, **previous/next relationships**, full **lineage** back to its source structural
element(s), and **structural context** (heading path, element type, source location) — all
assembled exclusively by the Chunk Builder, then checked by a dedicated Chunk Validation stage that
produces an explicit **Validation Report** (status, failed rules, warnings, messages) before the
result becomes the pipeline's output **Chunk Set** — all additive to, and backward-compatible
with, the existing chunk/citation/indexing contract. The
canonical structural-element vocabulary is extended (per the existing extensibility rule) with
`heading`, `code-block`, `quote`, and `figure-placeholder` so technical, quoted, and mixed-media
content is chunked as first-class semantic units instead of being absorbed into surrounding
paragraph text. The engine remains fully deterministic and reproducible: given the same Document
Model and configuration, it always produces the same chunks — no embeddings, no live model calls,
no randomness.

This feature's output is scoped to become the canonical input for a future **Knowledge
Representation** stage; it does not itself perform embedding, entity/relation extraction,
retrieval, ranking, planning, or answer generation.

### Architectural Verdict

| Approach | Verdict |
| -------- | ------- |
| **Strategy-based structural/semantic chunking over the Canonical Document Model, generic core + YAML strategy/config selection** | Preferred — meaning-preserving, swappable, deterministic, and consistent with the generic-core-plus-YAML-packs principle established by `006`. |
| **Current heuristic**: group adjacent same-type elements to a character budget, slice anything oversized | Superseded as the primary strategy — token-utilization-first, ignores heading/section semantics, no relationships/lineage/hierarchy. Its logic is retained only as the documented oversized-element split fallback. |
| **Per-domain custom chunkers** (e.g., a pharmacy-only chunking module) | Rejected — violates generic-core-plus-YAML-packs; reintroduces per-domain Python maintenance the platform is explicitly moving away from. |
| **Embedding/LLM-driven semantic boundary detection** | Rejected for this feature — would violate the "embeddings out of scope" constraint and the determinism/reproducibility requirement; reserved, if ever pursued, as a separate pluggable Boundary Decision Policy behind the same interface, not the default. |
| **Single opaque "context-coherence score" combining all signals into one number** | Superseded — replaced by an explicit Semantic Boundary Evaluator producing independent, inspectable Boundary Features per signal category, feeding a separately swappable Boundary Decision Policy; boundary reasoning is never a black box. |
| **Boundary Decision Policy assembling Chunk objects directly** | Rejected — collapses decision-making and chunk assembly into one component, defeating independent swappability of policies and builder logic; a dedicated Chunk Builder owns chunk assembly exclusively, and the Decision Policy is limited to emitting a Boundary Decision. |

---

## Architecture: Boundary Decision Pipeline

Every chunk-boundary decision — merge across a candidate boundary, or split at it — and its
eventual assembly into a Chunk, flows through one explicit pipeline. Each stage has exactly one
responsibility, and no stage performs another stage's job:

```
Document Model
        ↓
Boundary Candidates
        ↓
Semantic Boundary Evaluator
        ↓
Boundary Features
        ↓
Boundary Decision Policy
        ↓
Chunk Builder
        ↓
Chunk Validation
        ↓
Validation Report
        ↓
Chunk Set
```

- **Document Model** — the Canonical Document Model (`DocumentModel`/`StructuralElement`,
  produced by `006-document-intelligence-pipeline`) is the pipeline's sole input; no stage
  downstream re-parses raw source content.
- **Boundary Candidates** — every adjacent pair of Structural Elements (including sequences
  already provisionally grouped by earlier decisions) is a potential boundary the pipeline must
  resolve: merge across it, or split at it.
- **Semantic Boundary Evaluator** — for each Boundary Candidate, analyzes it against multiple
  independent signal categories — including but not limited to hierarchy continuity, heading
  continuity, section continuity, structural (element-type) compatibility, lexical continuity,
  table integrity, list integrity, code integrity, quote integrity, document layout continuity,
  and configured size budget — and produces a structured **Boundary Features** entity. The
  Evaluator computes features only: it never merges or splits content, never decides anything,
  and never collapses these signals into one score.
- **Boundary Features** (`BoundaryFeatures`) — the Evaluator's output for one Boundary Candidate:
  an explicit, deterministic, inspectable, and serializable entity with one independent field per
  signal category (e.g., `heading_continuity: true`, `table_integrity: false`,
  `size_budget: within_limit`) — never a single collapsed score. Features are exposed
  independently of any decision, so they can be logged, tested, and reused by any Decision Policy
  without re-running feature extraction (FR-044).
- **Boundary Decision Policy** — a swappable component that consumes one Boundary Candidate's
  Boundary Features and decides merge/split only, emitting a single **Boundary Decision** entity
  — `decision`, `applied_rule`, `triggered_features`, and `rationale` (FR-045) — never a
  probabilistic confidence score. The Decision Policy never computes features and never
  constructs, assembles, or mutates a Chunk — that is the Chunk Builder's job alone.
- **Chunk Builder** — builds chunks only, and does so **statefully**: it incrementally opens,
  appends to, and closes each chunk over the ordered stream of Boundary Decisions before assigning
  identity, building relationships, and emitting it (FR-047; see "Chunk Builder Lifecycle" below).
  It is the sole owner of any in-progress (not-yet-closed) chunk's state; it never evaluates
  boundary signals and never decides merge/split.
- **Chunk Validation** — validates output only: checks the Chunk Builder's output against the
  chunk quality rules and structural constraints (FR-021–FR-026), producing exactly one
  **Validation Report** entity (FR-046) before the result is finalized. It never assembles, merges,
  or splits chunks; it only inspects, filters, or flags (FR-043).
- **Validation Report** (`ValidationReport`) — Chunk Validation's structured, explicit output: an
  overall `status`, the set of `failed_rules` (if any), `warnings` (non-blocking issues), and
  human-inspectable `validation_messages` (FR-046). It is produced before the Chunk Set is
  returned, and is retained for observability/debugging independent of re-running chunking.
- **Chunk Set** — the ordered, complete collection of validated Chunks for one document, finalized
  only after Chunk Validation has produced its Validation Report and applied any documented
  auto-corrections: the pipeline's terminal output, and the unchanged contract downstream
  indexing/retrieval consumes (FR-031/FR-032).

### Chunk Builder Lifecycle (Stateful)

The Chunk Builder is not a single, stateless construction step — it incrementally assembles each
chunk over the ordered stream of Boundary Decisions for one document, and is the sole owner of any
in-progress chunk's state:

```
Boundary Decisions
        ↓
Open Chunk
        ↓
Append Structural Elements
        ↓
Close Chunk
        ↓
Assign Stable Identity
        ↓
Build Relationships
        ↓
Emit Chunk
```

- **Open Chunk** — begin accumulating a new, not-yet-identified chunk, when the previous chunk (if
  any) has just closed, or at the start of the document.
- **Append Structural Elements** — for each `merge` Boundary Decision, add the next Structural
  Element to the currently open chunk.
- **Close Chunk** — stop accumulating, triggered by a `split` Boundary Decision or the end of the
  document; the chunk's content is now fixed.
- **Assign Stable Identity** — only after closing, compute the chunk's deterministic identity
  (FR-008/FR-009); an open, not-yet-closed chunk MUST NOT have an identity yet.
- **Build Relationships** — construct the closed chunk's parent/child and previous/next links
  (FR-010–FR-012) relative to already-emitted chunks.
- **Emit Chunk** — add the finished chunk to the Chunk Set; the Chunk Builder's in-progress state
  for that chunk is cleared.

No component other than the Chunk Builder MUST construct or mutate a Chunk object at any point in
this lifecycle (FR-041/FR-042/FR-047).

**Separation of concerns**: the Semantic Boundary Evaluator, the Boundary Decision Policy, the
Chunk Builder, and Chunk Validation are each independently swappable/extensible. The Evaluator's
signal set can grow without changing any Decision Policy; a Decision Policy can change how it
weighs or combines signals without changing the Evaluator, the Chunk Builder, or the Chunking
Engine that calls the pipeline; the Chunk Builder's assembly logic can evolve without either
component upstream needing to change. This specification defines and requires only one Decision
Policy by default — deterministic and rule-based — while explicitly reserving the same interface
for future weighted-scoring, ML-based, or LLM-based policies (see Assumptions, Out of Scope, and
FR-033–FR-048).

**Responsibility boundaries** (no component performs another's job):

| Component | Responsible for | Never does |
| --------- | ---------------- | ---------- |
| Semantic Boundary Evaluator | Computing Boundary Features only | Deciding merge/split; constructing chunks |
| Boundary Decision Policy | Deciding merge/split only (emits a Boundary Decision) | Computing features; constructing chunks |
| Chunk Builder | Building chunks only, statefully (lifecycle, identity, relationships, lineage, structural metadata) | Evaluating signals; deciding merge/split |
| Chunk Validation | Validating the Chunk Set only (emits a Validation Report) | Assembling, merging, or splitting chunks |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Semantic boundaries over token utilization (Priority: P1)

A platform operator ingests a document whose Canonical Document Model contains headings,
paragraphs, a table, and a list. Today's chunker groups adjacent same-type elements up to a
character budget and blindly slices anything oversized, with no regard for whether a heading is
being separated from its content or a table is being fragmented mid-row. With the Intelligent
Chunking Engine, boundaries are chosen so each chunk represents a complete semantic unit — a
heading stays with its content, a table row is never fragmented, and unrelated sections are never
merged — even when that means a chunk is not maximally packed toward its size budget.

**Why this priority**: This is the entire premise of the feature — meaning preservation over
token-fitting — and every other requirement (relationships, lineage, validation) is built on top
of correct boundary decisions.

**Independent Test**: Feed a fixture Document Model containing headings with body text, a
multi-row table, and two distinct sections. Verify no chunk separates a heading from its
immediately following content, no chunk contains a partial table row, and no chunk mixes content
from two different sections.

**Acceptance Scenarios**:

1. **Given** a heading element followed by paragraph elements under it, **When** chunking runs,
   **Then** the heading and at least the first unit of its content share a chunk, or — if size
   forces a split — every resulting chunk under that heading retains the heading in its
   structural-context metadata.
2. **Given** a table with more rows than fit in one chunk, **When** chunking runs, **Then** splits
   occur only at row boundaries, never mid-row.
3. **Given** two adjacent but unrelated sections, **When** chunking runs, **Then** no chunk
   contains content from both sections.

---

### User Story 2 - Strategy-based, swappable chunking architecture (Priority: P1)

A platform maintainer wants to introduce a new chunking approach (e.g., a stricter section-only
strategy for legal documents, or a looser grouping strategy for chat-style transcripts) without
touching indexing, retrieval, or chunk storage code. With the Intelligent Chunking Engine, all
boundary-detection/merge/split logic sits behind one strategy interface, and strategies are
selected and configured declaratively. Swappability applies at two levels: whole chunking
strategies, and — within a strategy's Boundary Decision Pipeline — the Boundary Decision Policy
that turns Boundary Features into merge/split decisions (see "Architecture: Boundary Decision
Pipeline").

**Why this priority**: This is the extensibility backbone the feature exists to provide — without
it, every new document type or domain need re-introduces core changes, repeating the exact problem
this feature is meant to solve.

**Independent Test**: Add a second chunking strategy implementation and switch a project's
configuration to use it. Verify indexing, retrieval, and chunk storage continue to function
against the new strategy's output with zero code changes outside the new strategy and its
registration.

**Acceptance Scenarios**:

1. **Given** two chunking strategies registered in the engine, **When** a project's pack selects
   one via configuration, **Then** that strategy's boundary logic is used for its documents with
   no change to the engine's core dispatch logic.
2. **Given** a new strategy is added and registered, **When** existing projects continue running
   their current strategy, **Then** neither their behavior nor any downstream indexing/retrieval/
   storage code changes.
3. **Given** a Boundary Decision Policy is replaced with an alternative policy (e.g., a rule-based
   policy swapped for a weighted-scoring policy), **When** boundary candidates are evaluated,
   **Then** the Semantic Boundary Evaluator's feature extraction and the Chunking Engine's
   dispatch logic require no changes — only the policy implementation differs.

---

### User Story 3 - Hierarchical, relationship-aware chunk output (Priority: P1)

A retrieval pipeline wants to expand a matched chunk's context — show its parent section, or the
previous/next chunk — when composing an answer. With the Intelligent Chunking Engine, every chunk
carries parent/child hierarchy links and previous/next adjacency links, in addition to today's
flat ordered chunk list.

**Why this priority**: This unlocks context-aware answer composition and is a direct prerequisite
for the future Knowledge Representation stage this feature's output must feed; it is one of the
explicitly requested chunk relationship capabilities.

**Independent Test**: Chunk a fixture document with a nested section/subsection/paragraph
structure. Verify every child chunk references a valid parent chunk id, every chunk (except the
first/last) references valid previous/next chunk ids, and following those links reconstructs the
original document order and hierarchy.

**Acceptance Scenarios**:

1. **Given** a section containing multiple paragraphs, **When** chunking runs, **Then** the
   section is represented as a parent grouping referencing its paragraph-level child chunks.
2. **Given** the full ordered chunk output for a document, **When** previous/next links are
   followed starting from the first chunk, **Then** every chunk in the document is visited exactly
   once, in original document order.

---

### User Story 4 - Stable identity, lineage, and reproducibility (Priority: P2)

An operator re-processes the same document (retry, re-index) and needs the resulting chunks to be
traceable back to exactly which structural elements produced them, and identical to the previous
run so nothing is duplicated, renumbered, or silently changed.

**Why this priority**: Required for production trust, debuggability, and idempotent re-ingestion;
required for this feature's output to be usable as the "canonical input" for a future stage.

**Independent Test**: Chunk the same fixture Document Model twice with the same configuration.
Verify chunk ids, text, relationships, and lineage are identical between runs, and that every
chunk's lineage correctly names its source structural element id(s) and the rule that produced it.

**Acceptance Scenarios**:

1. **Given** an unchanged Document Model and configuration, **When** chunking runs twice, **Then**
   both runs produce identical chunk ids, text, and relationships.
2. **Given** any produced chunk, **When** its lineage is inspected, **Then** it names the exact
   source structural element id(s) and the merge/split/group rule that produced it.

---

### User Story 5 - Extended structural awareness: code, quotes, figures, headings (Priority: P2)

A document contains a heading, a code sample, a block quote, and a referenced figure. Today's
chunker only understands section/paragraph/table/list types and would silently absorb these into
surrounding paragraph text, losing their distinct meaning. With the Intelligent Chunking Engine,
these are recognized as first-class structural types and chunked as atomic, addressable units.

**Why this priority**: Explicitly requested awareness categories; without them, technical,
legal-quotation, and mixed-media documents lose meaning-bearing structure that generic chunking
should preserve.

**Independent Test**: Chunk a fixture Document Model containing a heading, a code block, a block
quote, and a figure placeholder interleaved with paragraphs. Verify each becomes its own distinct,
non-empty chunk (or a documented, explicitly-configured group) rather than being merged into
unrelated paragraph text.

**Acceptance Scenarios**:

1. **Given** a code-block element surrounded by paragraph elements, **When** chunking runs,
   **Then** the code block is not merged with the surrounding paragraphs into one chunk.
2. **Given** a figure-placeholder element, **When** chunking runs, **Then** it produces its own
   chunk carrying figure provenance, even when it has little or no text.

---

### User Story 6 - Automated chunk quality validation gate (Priority: P3)

Before chunk output reaches indexing, the platform wants an automatic check that no degenerate
chunk (empty, orphaned heading, cross-section merge, oversized unsplit fragment) slips through,
regardless of which strategy produced it.

**Why this priority**: A safety net that makes every other guarantee in this spec enforceable and
observable; the pipeline can function while other stories land first, hence P3.

**Independent Test**: Run chunking on a fixture set that includes intentionally malformed inputs
designed to trigger every quality rule. Verify each violation is either corrected per a documented
rule or surfaced as an explicit validation failure, with no violation reaching output silently.

**Acceptance Scenarios**:

1. **Given** a chunk candidate that is empty or whitespace-only, **When** validation runs, **Then**
   it is filtered out or flagged rather than passed to output.
2. **Given** a chunk set containing a rule violation, **When** validation completes, **Then** a
   Validation Report (status, failed rules, warnings, messages) is available for inspection
   without re-running chunking.

---

### Edge Cases

- A structural-element sequence with no headings at all (plain prose) → still produces valid
  semantic chunks via generic boundary rules; a heading is never required.
- A single structural element that legitimately exceeds the maximum chunk size even after all
  merge/split rules are applied → the documented, explicit oversized-element split exception
  applies; it MUST never happen silently or unrecorded in lineage.
- Two adjacent sections with different heading levels (nested subsections) → hierarchy correctly
  nests the deeper heading under its parent section rather than flattening both to the same level.
- A table so large it must span multiple chunks → splits occur only at row boundaries, and the
  resulting chunks remain linked via previous/next plus shared parent/table metadata so downstream
  consumers can reconstruct the full table if needed.
- A quote or code-block element that is empty or whitespace-only → excluded or flagged by the
  chunk quality validation gate rather than producing a degenerate empty chunk.
- A figure element with no extractable text (only a placeholder marker) → represented as its own
  low-content chunk carrying figure provenance, never merged into unrelated surrounding text.
- Re-chunking the same unchanged Document Model (idempotent re-ingestion) → produces exactly the
  same chunk ids, text, and relationships; no duplication, no silent renumbering.
- A pack/strategy configuration missing or conflicting for a given element type → the engine falls
  back to documented generic defaults rather than crashing or silently dropping content.
- A Document Model marked `extraction_outcome: degraded` (single fallback element, per `006`) →
  the engine still runs its generic boundary logic on that lone element; no special-cased "degraded
  mode" branch is introduced.
- A structural element type the engine has no explicit rule for (forward-compatible future type) →
  falls back to paragraph-equivalent handling rather than raising, per the existing vocabulary
  forward-compatibility rule.

## Requirements *(mandatory)*

### Functional Requirements

#### Input Contract & Generic Architecture

- **FR-001**: The chunking engine MUST consume only the Canonical Document Model
  (`DocumentModel`/`StructuralElement`, produced by `006-document-intelligence-pipeline`) as its
  input; it MUST NOT parse or read raw PDF, DOCX, HTML, Markdown, or other source-file content
  directly.
- **FR-002**: The chunking engine's core logic MUST NOT contain any domain-name-specific
  conditionals; all domain-specific chunking behavior MUST be expressed as declarative
  configuration (strategy selection and parameters) consumed by generic code, following the
  existing generic-core-plus-YAML-packs precedence (generic < domain < project).
- **FR-003**: The engine MUST support every document type uniformly by depending only on the
  canonical structural-element vocabulary, never on the originating source file format.

#### Extended Structural Vocabulary

- **FR-004**: The canonical structural-element vocabulary MUST be extended, in a
  backward-compatible way, with `heading`, `code-block`, `quote`, and `figure-placeholder`
  alongside the existing `section`/`paragraph`/`table`/`table-row`/`list`/`list-item` types,
  without changing the meaning or handling of the existing types.
- **FR-005**: Any consumer (chunking engine, downstream indexing/retrieval) encountering a
  structural-element type it has no explicit rule for MUST fall back to paragraph-equivalent
  handling rather than raising an error.
- **FR-006**: By default, `code-block` and `quote` elements MUST be treated as atomic semantic
  units — not split mid-block and not merged with unrelated surrounding text — unless a pack
  explicitly configures different behavior.
- **FR-007**: `figure-placeholder` elements MUST be represented as their own addressable chunk
  carrying figure provenance, even when they contain little or no text.

#### Chunk Model & Identity

- **FR-008**: Every produced chunk MUST carry a stable, deterministic identity derived from its
  source structural-element id(s), the owning document's identity, and the chunking
  strategy/configuration in effect, such that re-chunking unchanged input with unchanged
  configuration always yields the same chunk id.
- **FR-009**: Every produced chunk MUST record the non-empty set of structural element(s) it was
  derived from, the canonical element type it represents, its ordered position within the
  document, and its structural context (e.g., enclosing heading/section path).

#### Chunk Relationships & Hierarchy

- **FR-010**: The engine MUST support parent/child chunk relationships, so a higher-level semantic
  unit (e.g., a section) can be represented alongside its finer-grained children (e.g., the
  paragraphs within it), without requiring changes to how children are individually stored or
  retrieved.
- **FR-011**: The engine MUST record previous/next chunk relationships reflecting document reading
  order, enabling downstream consumers to expand context around a retrieved chunk.
- **FR-012**: All chunk relationships MUST be internally consistent — every referenced
  parent/child/previous/next chunk id MUST correspond to an actual chunk produced in the same
  chunking run; dangling references are not permitted.

#### Chunk Lineage & Traceability

- **FR-013**: Every produced chunk MUST preserve full lineage back to its originating structural
  element(s) — and transitively to the source document/asset — sufficient to explain exactly which
  elements were merged, grouped, or split, and by which rule, to produce that chunk.
- **FR-014**: Chunk lineage and identity MUST be fully reproducible: reprocessing the same
  unchanged Document Model with the same configuration MUST produce chunks with identical ids,
  text, relationships, and lineage.

#### Boundary Detection, Semantic Merge & Split Rules

*Every boundary between adjacent Structural Elements is decided by routing it, as a Boundary
Candidate, through the Semantic Boundary Evaluator and a Boundary Decision Policy defined in
"Semantic Boundary Evaluator & Boundary Decision Policy" below (FR-033–FR-040). FR-015 anchors
this as the engine's boundary-decision mechanism; FR-016–FR-020 constrain what the resulting
decisions are, and are not, allowed to produce.*

- **FR-015**: The engine MUST decide chunk boundaries dynamically by routing every candidate
  boundary between adjacent Structural Elements through the Semantic Boundary Evaluator and a
  Boundary Decision Policy (FR-033–FR-040) — never through fixed token/character-window slicing
  as the primary strategy; fixed-window slicing remains only the documented oversized-element
  fallback (FR-018).
- **FR-016**: Semantic merge rules MUST combine adjacent, compatible structural elements into one
  chunk only when doing so preserves a complete semantic unit (e.g., a heading with its
  immediately following content, or consecutive short list items of the same list) and stays
  within the configured size limit.
- **FR-017**: Semantic merge rules MUST NOT combine structural elements belonging to different,
  unrelated sections/headings into a single chunk, regardless of how small each element is.
- **FR-018**: Semantic split rules MUST only split a structural element when it exceeds the
  configured maximum chunk size, MUST prefer splitting at the largest available sub-boundary
  (e.g., paragraph, sentence, or row boundary) before falling back to a raw character/token cut,
  and every such split MUST be explicit and recorded in the resulting chunks' lineage.
- **FR-019**: A heading/title element MUST NOT be separated from the content it introduces across
  a chunk boundary unless their combined size exceeds the configured limit; when a split is
  unavoidable, the heading MUST still be present in the structural-context metadata of every
  resulting chunk under it.
- **FR-020**: A table MUST NOT be split into fragments that omit its column/table context; when a
  table must span multiple chunks, each resulting chunk MUST retain enough structural context
  (e.g., table/section identity, header reference) to be understood on its own.

#### Structural Constraints & Chunk Quality Rules

- **FR-021**: Chunking MUST NOT split a paragraph, list item, or table row unless it individually
  exceeds the configured maximum chunk size (the documented oversized-element exception only).
- **FR-022**: Chunking MUST NOT merge structural elements belonging to different parent sections
  into one chunk, even when both are well under the size limit.
- **FR-023**: Every produced chunk MUST satisfy a minimum-content quality rule (non-empty,
  non-whitespace-only text or field mapping); chunks that fail this rule MUST be filtered or
  flagged, never silently passed downstream.
- **FR-024**: Every produced chunk MUST satisfy a maximum-size quality rule (at or below the
  configured limit, except the documented oversized-element exception) before being accepted as
  output.

#### Chunk Validation

- **FR-025**: The engine MUST validate every produced chunk set against the quality rules and
  structural constraints above before returning output, recording the outcome as a
  `ValidationReport` (FR-046); violations MUST be either auto-corrected via a documented rule or
  surfaced as an explicit validation failure — never silently passed downstream.
- **FR-026**: The `ValidationReport` (status, failed rules, warnings, and messages — FR-046) MUST
  be available for observability and debugging without requiring the chunking engine to be
  re-run.

#### Strategy Architecture & Extension Points

- **FR-027**: The chunking engine MUST be strategy-based: boundary-detection, merge, and split
  logic MUST be swappable behind one stable interface, without requiring any change to indexing,
  retrieval, or chunk storage code that consumes the engine's output.
- **FR-028**: New chunking strategies MUST be addable by implementing the existing strategy
  interface and registering it, without modifying the generic engine's core dispatch logic.
- **FR-029**: Domain and project packs MUST be able to select and configure which chunking
  strategy applies, and its parameters, via the existing YAML pack precedence (generic < domain <
  project).
- **FR-030**: The chunking stage MUST remain fully deterministic and reproducible for a given
  Document Model, strategy, and configuration; no strategy shipped by default with this feature
  MAY introduce non-deterministic behavior (e.g., randomized tie-breaking, uncached live model
  calls) into its output.

#### Output Contract

- **FR-031**: Chunk output MUST remain compatible with the existing chunk/citation/indexing
  contract (chunk text, chunk metadata, chunk order) so that retrieval, indexing, and storage
  require zero changes to consume the new engine's output.
- **FR-032**: Existing chunk metadata keys relied upon by current citation and field-resolution
  logic MUST continue to be populated; new identity, hierarchy, relationship, and lineage fields
  MUST be additive, never replacing or removing existing keys.

#### Semantic Boundary Evaluator & Boundary Decision Policy

- **FR-033**: The Semantic Boundary Evaluator MUST expose the extracted Boundary Features
  independently of the final Boundary Decision, allowing downstream Decision Policies to evolve
  without modifying feature extraction.
- **FR-034**: Every adjacent pair of Structural Elements (including sequences already
  provisionally grouped by prior merge decisions) MUST be treated as a Boundary Candidate that
  the pipeline evaluates; the engine MUST NOT decide a merge or split without first producing a
  Boundary Candidate for the Semantic Boundary Evaluator to analyze.
- **FR-035**: For every Boundary Candidate, the Semantic Boundary Evaluator MUST analyze, at
  minimum, the following independent signal categories and record each as a distinct field of
  Boundary Features: hierarchy continuity, heading continuity, section continuity, structural
  (element-type) compatibility, lexical continuity, table integrity, list integrity, code
  integrity, quote integrity, document layout continuity, and configured size budget. Additional
  signal categories MAY be added without changing the Boundary Decision Policy interface.
- **FR-036**: The Semantic Boundary Evaluator MUST NOT itself decide to merge or split content and
  MUST NOT construct, assemble, or mutate a Chunk; its sole output per Boundary Candidate is the
  `BoundaryFeatures` entity described in FR-033, FR-035, and FR-044.
- **FR-037**: The Semantic Boundary Evaluator MUST be fully deterministic and MUST NOT use
  embeddings, vector similarity, LLM inference, or any other probabilistic runtime behavior to
  produce Boundary Features, regardless of which Boundary Decision Policy is active downstream.
- **FR-038**: The Boundary Decision Policy MUST be swappable behind a stable interface,
  independent of the Semantic Boundary Evaluator, the Chunk Builder, and the Chunking Engine; a
  Boundary Decision Policy consumes one Boundary Candidate's `BoundaryFeatures` (FR-044) and MUST
  return exactly one `BoundaryDecision` entity (FR-045) — deciding merge/split only, and never
  constructing, assembling, or mutating a Chunk. New policies (e.g., weighted-scoring, ML-based,
  LLM-based) MUST be addable by implementing this interface, without modifying the Evaluator's
  feature extraction, the Chunk Builder's assembly logic, or the engine's dispatch logic.
- **FR-039**: The default Boundary Decision Policy defined by this specification MUST be
  deterministic and rule-based, resolving Boundary Features through explicit, documented rules
  (not learned weights or model inference); any non-deterministic or probabilistic policy is an
  optional, explicitly-configured alternative and MUST NOT be the default.
- **FR-040**: Every Boundary Decision MUST be recorded as part of the resulting chunk(s)' lineage
  (FR-013), identifying the Boundary Candidate, the Boundary Features considered, the Boundary
  Decision Policy that produced the decision, and the decision itself (merge or split).

#### Chunk Builder & Component Ownership

- **FR-041**: The Chunk Builder MUST be the sole component responsible for assembling Chunk
  objects from Boundary Decisions and their source Structural Element(s), and for satisfying the
  chunk identity (FR-008/FR-009), relationship (FR-010–FR-012), and lineage (FR-013) requirements;
  no other component (Semantic Boundary Evaluator, Boundary Decision Policy, Chunk Validation)
  MUST perform any of these responsibilities.
- **FR-042**: The Boundary Decision Policy MUST NOT construct, assemble, or mutate Chunk objects
  under any circumstance; its output MUST be limited to exactly one `BoundaryDecision` per
  Boundary Candidate (FR-045), consumed exclusively by the Chunk Builder.
- **FR-043**: Chunk Validation MUST operate only on the Chunk Set produced by the Chunk Builder,
  applying the quality rules and structural constraints already defined (FR-021–FR-026) and
  recording the result as a `ValidationReport` (FR-046); it MUST NOT itself assemble, merge, or
  split chunks, nor alter chunk boundaries beyond the documented filter/flag actions (FR-025).
- **FR-044**: `BoundaryFeatures` MUST be exposed as an explicit, structured entity with one
  independently inspectable, deterministic, and serializable field per required signal category
  (FR-035): `hierarchy_continuity`, `heading_continuity`, `section_continuity`,
  `structural_compatibility`, `lexical_continuity`, `table_integrity`, `list_integrity`,
  `code_integrity`, `quote_integrity`, `layout_continuity`, and `size_budget`. `BoundaryFeatures`
  MUST be reusable, unmodified, by any Boundary Decision Policy without re-running feature
  extraction.
- **FR-045**: `BoundaryDecision` MUST be exposed as an explicit, structured entity containing at
  minimum a `decision` (`merge` | `split`), an `applied_rule` identifying which rule of the active
  Boundary Decision Policy produced the decision, `triggered_features` identifying the specific
  `BoundaryFeatures` field(s) that determined the decision, and a `rationale` feeding chunk
  lineage (FR-040). `BoundaryDecision` MUST NOT include a probabilistic confidence score or any
  other non-deterministic field. Every Boundary Decision Policy implementation MUST return this
  entity, and nothing else, as its output.

#### Chunk Lifecycle, Explainability & Validation Output

- **FR-046**: Chunk Validation MUST produce exactly one `ValidationReport` entity per chunking
  run, before the Chunk Set is returned as output. `ValidationReport` MUST be an explicit,
  structured entity containing, at minimum: an overall validation `status`, the set of
  `failed_rules` (if any), a set of `warnings` (non-blocking issues), and human-inspectable
  `validation_messages`. Chunk Validation MUST NOT return a bare pass/fail boolean in place of a
  `ValidationReport`.
- **FR-047**: The Chunk Builder MUST manage every chunk's assembly through an explicit, ordered
  lifecycle over the stream of Boundary Decisions for one document: open a new chunk, append the
  Structural Element(s) each `merge` decision keeps together, close the chunk (on a `split`
  decision or end of document), assign its stable identity (FR-008/FR-009), build its
  relationships (FR-010–FR-012), and emit it into the Chunk Set. The Chunk Builder MUST NOT assign
  identity or build relationships for a chunk that has not yet been closed, and remains the sole
  owner of any in-progress (not-yet-closed) chunk's state.
- **FR-048**: Every `BoundaryDecision`'s fields (FR-045) MUST be sufficient, on their own, to
  explain why the decision was made — without re-running the Semantic Boundary Evaluator or the
  active Boundary Decision Policy — enabling deterministic replay and independent audit of any
  chunk boundary.

### Key Entities

- **Chunk (extended)**: A retrieval-ready unit derived from one or more Structural Elements;
  extends the existing Chunk entity from `006-document-intelligence-pipeline` with a stable
  identity, hierarchy/adjacency relationships, and lineage, in addition to its existing text and
  inherited provenance metadata.
- **Chunk Identity**: A deterministic identifier derived from source structural-element id(s),
  document identity, and the chunking strategy/configuration fingerprint in effect; stable across
  repeated processing runs of unchanged input.
- **Chunk Relationships**: Parent/child links (hierarchical containment — a section-level chunk
  and its finer-grained children) and previous/next links (reading-order adjacency) between chunks
  of the same document.
- **Chunk Lineage**: The recorded trail of which structural element(s), and which merge/split/
  grouping rule, produced a given chunk — sufficient to explain and reproduce that chunk's
  boundaries on demand.
- **Chunk Quality Rule**: A named, testable constraint that a produced chunk (or chunk set) must
  satisfy — e.g., minimum content, maximum size, no orphaned heading, no cross-section merge, no
  mid-row table split.
- **Validation Report** (`ValidationReport`): The formal, structured outcome of Chunk Validation —
  containing `status`, `failed_rules`, `warnings`, and `validation_messages` (FR-046) — produced
  exactly once per chunking run, before the Chunk Set is returned, and observable independently of
  re-running chunking. (Supersedes the informally-described "Chunk Validation Result" outcome —
  same concept, now a named entity with a fixed shape.)
- **Boundary Candidate**: A potential boundary point between two adjacent Structural Elements (or
  provisionally-grouped element sequences) that the Boundary Decision Pipeline evaluates for a
  merge-or-split outcome.
- **Semantic Boundary Evaluator**: The component responsible for analyzing every Boundary
  Candidate across multiple independent signal categories (hierarchy continuity, heading
  continuity, section continuity, structural compatibility, lexical continuity, table integrity,
  list integrity, code integrity, quote integrity, document layout continuity, and configured
  size budget) and producing a structured Boundary Features entity; it computes features only —
  it never merges or splits content and never constructs a Chunk.
- **Boundary Features** (`BoundaryFeatures`): The Evaluator's structured, per-signal output for
  one Boundary Candidate — an explicit, deterministic, inspectable, and serializable entity
  exposing one independent field per required signal category: `hierarchy_continuity`,
  `heading_continuity`, `section_continuity`, `structural_compatibility`, `lexical_continuity`,
  `table_integrity`, `list_integrity`, `code_integrity`, `quote_integrity`, `layout_continuity`,
  and `size_budget` (FR-044) — never a single collapsed score, and reusable, unmodified, by any
  Decision Policy.
- **Boundary Decision Policy**: A swappable component that consumes one Boundary Candidate's
  Boundary Features and produces a Boundary Decision; conforms to one stable interface so
  rule-based, weighted-scoring, ML-based, or LLM-based policies can be substituted without
  changing the Semantic Boundary Evaluator, the Chunk Builder, or the Chunking Engine. The default
  policy defined by this specification is deterministic and rule-based. It decides merge/split
  only and never constructs a Chunk (FR-042).
- **Boundary Decision** (`BoundaryDecision`): The final outcome for one Boundary Candidate,
  produced by the active Boundary Decision Policy from that candidate's Boundary Features — an
  explicit entity containing at minimum `decision` (`merge` | `split`), `applied_rule`,
  `triggered_features` (the specific Boundary Features field(s) that drove the decision), and
  `rationale` (FR-045) — sufficient on its own to explain the decision (FR-048), never a bare
  boolean, never a probabilistic confidence score, and never an assembled Chunk. Consumed
  exclusively by the Chunk Builder.
- **Chunk Builder**: The stateful component solely responsible for assembling Chunk objects,
  incrementally, over the ordered stream of Boundary Decisions for one document: opening a chunk,
  appending Structural Elements, closing the chunk, then assigning its stable identity
  (FR-008/FR-009), constructing its parent/child and previous/next relationships (FR-010–FR-012),
  recording its lineage (FR-013), and attaching its structural metadata (FR-041/FR-047 — see
  "Chunk Builder Lifecycle"). It is the sole owner of any in-progress chunk's state; it never
  evaluates boundary signals and never decides merge/split.
- **Chunk Validation** (stage): The pipeline stage that checks the Chunk Set produced by the Chunk
  Builder against every Chunk Quality Rule and structural constraint, producing exactly one
  Validation Report (FR-043/FR-046). It validates output only — it never assembles, merges, or
  splits chunks.
- **Chunk Set**: The ordered, complete collection of Chunks the Chunk Builder produces for one
  document, finalized after Chunk Validation produces its Validation Report and applies any
  documented auto-corrections — the Boundary Decision Pipeline's terminal output, handed to
  indexing/retrieval unchanged.
- **Chunking Strategy**: A swappable implementation of boundary-detection/merge/split behavior,
  selected and configured per domain/project pack, conforming to one stable strategy interface.
- **Extended Structural Element Types**: `heading`, `code-block`, `quote`, `figure-placeholder` —
  new canonical vocabulary values, alongside the existing six, that the chunking engine treats as
  first-class semantic units.

### Non-Functional Requirements *(constitution-aligned)*

- **NFR-001**: The chunking engine MUST respect Clean Architecture layering: strategy/boundary
  logic lives in core/application, orchestration in existing Celery tasks; no domain-specific
  Python outside declarative pack configuration.
- **NFR-002**: Chunking strategy selection MUST be swappable via a factory/registry (constitution
  Principle V), never via conditional branching in callers.
- **NFR-003**: The chunking engine is CPU-bound and MUST NOT introduce blocking network or live
  model calls into its default strategies; existing async/Celery task boundaries are unchanged.
- **NFR-004**: The engine and its default strategies MUST be fully deterministic and reproducible;
  no dependency on wall-clock time, randomness, or non-deterministic external calls.
- **NFR-005**: Public strategy interfaces and chunk/relationship/lineage model classes MUST
  include type hints (Pydantic models), consistent with existing `core/document_intelligence/`
  conventions.
- **NFR-006**: Unit and integration tests MUST cover: boundary/merge/split behavior per structural
  constraint, relationship/lineage integrity, determinism (repeat-run equality), quality-rule
  validation, and strategy swappability (zero downstream contract change).
- **NFR-007**: Structured logging MUST record, at minimum, per-asset chunk counts by element type,
  validation rule pass/fail counts, and which strategy was applied, at existing Celery task
  logging boundaries.
- **NFR-008**: No secrets or credentials are introduced by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fixture set of documents containing headings, 100% of headings remain in the
  same chunk as at least the first unit of their content, or otherwise are present in the
  structural-context metadata of every chunk produced under them.
- **SC-002**: On a fixture set containing tables and lists, 100% of table rows and list items
  are represented as complete, unsplit units in the output chunks (zero mid-row or mid-item
  splits).
- **SC-003**: For a fixed Document Model and configuration, repeated chunking runs produce
  identical chunk ids, text, order, and relationships 100% of the time.
- **SC-004**: Swapping the active chunking strategy for a fixture project requires zero code
  changes outside the chunking module — verified by a documented smoke test showing zero diffs
  under indexing, retrieval, and storage code paths.
- **SC-005**: On a fixture set, 100% of produced chunks have referentially valid parent/child and
  previous/next relationship ids (zero dangling references) and can be traced back to their exact
  source structural element id(s).
- **SC-006**: On a fixture set containing code blocks, quotes, and figure placeholders, each such
  element is represented as its own distinct, non-empty chunk (or an explicitly documented group)
  in 100% of cases, with zero domain-specific code added to produce this behavior.
- **SC-007**: On a fixture set of intentionally malformed chunk candidates (empty, orphaned
  heading, cross-section merge, oversized unsplit fragment), the validation gate catches 100% of
  injected violations with zero false negatives, with each violation reflected in the resulting
  Validation Report's `failed_rules` or `warnings`.
- **SC-008**: End-to-end chunking time for a representative fixture set does not regress by more
  than an agreed threshold versus the current heuristic chunker (exact budget set during
  planning, measured against a recorded baseline).
- **SC-009**: For a fixed Boundary Candidate (same pair of Structural Elements, same
  configuration), the Semantic Boundary Evaluator produces identical Boundary Features across
  repeated runs 100% of the time, independent of which Boundary Decision Policy is active.
- **SC-010**: Swapping the active Boundary Decision Policy while holding the Semantic Boundary
  Evaluator and Chunking Engine fixed requires zero code changes outside the policy implementation
  — verified by a documented smoke test showing zero diffs under the Evaluator and engine dispatch
  code paths.
- **SC-011**: On a fixture set of Boundary Candidates constructed so each of the eleven required
  `BoundaryFeatures` fields independently varies in at least one case, the resulting Boundary
  Features reflect that variation per-field rather than being collapsed into one opaque score,
  confirming every signal is independently inspectable and serializable.
- **SC-012**: On a fixture set, 100% of chunks in the resulting Chunk Set are traceable to exactly
  one Chunk Builder invocation per Boundary Decision — verified by an architecture/contract check
  that no Boundary Decision Policy implementation returns anything other than a `BoundaryDecision`
  (i.e., no policy ever emits a Chunk object directly).
- **SC-013**: On a fixture set, 100% of `BoundaryFeatures` and `BoundaryDecision` instances
  round-trip through serialization (e.g., encode then decode) without loss, confirming both
  entities are genuinely serializable as required by FR-044/FR-045.
- **SC-014**: On a fixture set, 100% of produced `ValidationReport` instances agree with an
  independent re-evaluation of the same Chunk Set against the same quality rules and structural
  constraints (zero missing or fabricated `failed_rules`/`warnings`), confirming the report is a
  faithful, non-lossy summary rather than a bare pass/fail flag.
- **SC-015**: On a fixture set, 100% of `BoundaryDecision` instances have a non-empty
  `triggered_features` referencing only fields present in that candidate's `BoundaryFeatures`, and
  replaying the same features through the same rule independently reproduces an identical
  decision — confirming both explainability (FR-048) and determinism.
- **SC-016**: On a fixture set, tracing any single chunk's build lifecycle shows it was never
  assigned an identity or relationship before being closed (FR-047), and zero `BoundaryDecision`
  or `ValidationReport` instances contain a numeric confidence/probability field.

## Assumptions

- This feature builds directly on the already-implemented `006-document-intelligence-pipeline`
  Canonical Document Model; it replaces `map_elements_to_chunks`'s chunk-shaping behavior only —
  it does not re-parse raw files or change any format parser's element extraction.
- Extending the canonical structural-element vocabulary with `heading`, `code-block`, `quote`,
  and `figure-placeholder` is within scope for this feature (per the existing, explicitly stated
  extensibility rule for the vocabulary); retrofitting every existing format parser to emit all
  four new types is not required by this feature — the engine MUST handle these types generically
  wherever they are present and MUST NOT break when a parser never emits them (forward-compat
  fallback per FR-005).
- The default, deterministic, rule-based Boundary Decision Policy's exact per-signal precedence
  and tie-breaking (e.g., how a hierarchy-continuity signal is weighed against a size-budget
  signal when they disagree) is an implementation-phase (`/speckit-plan`) decision; this spec
  fixes the required signal categories (FR-035), the Evaluator/Policy separation (FR-033/FR-036),
  and the requirement that the default resolution be deterministic and rule-based (FR-039) — not
  the exact rule ordering. This preserves the stated "embeddings out of scope" constraint and full
  determinism at the feature-extraction layer regardless of which policy is later plugged in.
- `BoundaryFeatures` and `BoundaryDecision` are specified here as logical entities — their named
  fields (FR-044/FR-045) are fixed by this spec; the concrete class/model implementation (e.g., a
  typed Pydantic model, consistent with existing `core/document_intelligence/` conventions) is an
  implementation-phase decision.
- Splitting chunk assembly into its own Chunk Builder component does not change what a chunk must
  contain (FR-008–FR-014 are unchanged); it only fixes which component is accountable for
  producing that content, so existing chunk output/metadata contracts (FR-031/FR-032) are
  unaffected by this ownership clarification.
- The Chunk Builder's per-chunk lifecycle (open/append/close/assign-identity/build-relationships/
  emit, FR-047) governs one document's chunk stream in order; whether an implementation processes
  documents sequentially or with bounded concurrency across documents is an implementation-phase
  decision, constrained only by the requirement that within one document, lifecycle ordering and
  full determinism (FR-030/FR-047) are preserved.
- `ValidationReport.failed_rules`/`warnings` reference the named Chunk Quality Rules and
  structural constraints already defined in this spec (FR-021–FR-024); this feature formalizes how
  their outcomes are reported, and does not introduce new quality rules beyond that.
- `BoundaryDecision.triggered_features` references a subset of the existing `BoundaryFeatures`
  fields (FR-035/FR-044); it does not require the Semantic Boundary Evaluator to compute any
  additional signal beyond those already required.
- Chunk identity, hierarchy, relationships, and lineage are carried as part of the chunk output/
  metadata contract (additive fields), mirroring how `006` added `source_element_ids`/
  `element_type` without a storage-schema change; the exact persistence representation is a
  planning-phase decision, constrained only by the requirement that existing chunk storage,
  indexing, and retrieval keep working unchanged.
- The default chunking strategy shipped with this feature reproduces behavior equivalent to
  today's element-grouping semantics for domains that do not opt into a different strategy, so
  existing packs (`generic`/`pharmacy`/`legal`) are not unexpectedly regressed; domains opt into
  new strategies deliberately via configuration.
- This feature governs the chunking stage only. Embedding generation, entity/relation extraction,
  retrieval, ranking/fusion, reranking, query planning, and answer generation remain entirely
  unchanged consumers of this stage's (now richer) chunk output.
- The future "Knowledge Representation" stage referenced as this feature's downstream consumer is
  not yet a specified feature; this spec only commits to producing chunk output suitable as its
  canonical input (stable identity, hierarchy, relationships, lineage), not to that stage's design.

## Out of Scope

- Embedding generation, entity extraction, relation extraction, retrieval, ranking/fusion,
  reranking, query planning, and answer generation (explicit user-stated exclusions).
- Adding new raw source-format parsers or changing OCR providers/engines (unchanged from `006`).
- Retrofitting every existing format parser to detect and emit `heading`/`code-block`/`quote`/
  `figure-placeholder` elements — this feature makes the chunking engine capable of handling them
  generically; expanding parser coverage for each format is separate, incremental work.
- Any new database schema/table for chunk relationships or lineage — the output contract must
  remain compatible with the existing chunk storage shape (see FR-031/FR-032); schema changes, if
  ever needed, are a separate decision outside this spec.
- Designing the future Knowledge Representation stage itself — this feature only produces
  compatible input for it.
- Domain-specific (pharmacy, legal, etc.) chunking code added to core — all such behavior must be
  expressed via strategy selection/configuration per this spec's constraints.
- Implementing non-default Boundary Decision Policies (weighted-scoring, ML-based, LLM-based) —
  this spec requires only that the Boundary Decision Policy interface support them and ships the
  deterministic, rule-based default (FR-038/FR-039); building alternative policies is separate,
  future work.

## Dependencies

- `006-document-intelligence-pipeline` — **hard dependency**; this feature's sole input is the
  Canonical Document Model (`DocumentModel`/`StructuralElement`) this spec produces, and this
  feature extends its structural-element vocabulary and supersedes its `map_elements_to_chunks`
  chunk-shaping behavior.
- `002-field-registry` — field-pack precedence (generic < domain < project) that strategy
  selection/configuration builds on.
- `003-architecture-refactor` — `core/`/`services/` layering that hosts the new chunking engine.
- `005-answer-quality` — downstream beneficiary; richer, relationship-aware, meaning-preserving
  chunks are expected to further improve AQ-1/AQ-2 retrieval-coverage metrics, though this feature
  does not itself change retrieval or scoring.
- Future **Knowledge Representation** stage (not yet specified) — this feature's output is scoped
  to serve as its canonical input.

# Feature Specification: Architecture Consolidation

**Feature Branch**: `016-architecture-consolidation`

**Created**: 2026-07-18

**Updated**: 2026-07-18

**Status**: Draft

**Input**: Design architecture consolidation for duplicated implementations, architectural drift, and multiple execution paths. Objectives: single execution path per capability, single chunking pipeline, single retrieval pipeline, single canonical contracts, eliminate duplicated ownership, remove dead production paths, define ownership governance, enforce dependency direction, preserve generic architecture. Define canonical architecture, disposition strategy, migration order, compatibility, risks, and validation. Architecture plan only — no implementation tasks.

**Artifact type**: Architecture plan and governance baseline. Implementation task breakdown is out of scope.

---

## Scope

### In Scope

- Architectural principles, invariants, anti-patterns, and governance rules
- Logical capabilities, required concerns, contracts, and dependency boundaries
- Ownership rules, owner selection criteria, and lifecycle disposition
- Migration order, compatibility strategy, risks, and multi-category validation
- Architecture Decision Records for genuine tradeoffs

### Out of Scope

The following are explicitly excluded from this specification. They MUST NOT expand review or delivery scope under the guise of consolidation:

- Performance optimization and latency tuning
- Retrieval or ranking algorithm improvements
- Answer or retrieval quality tuning beyond cutover regression gates
- Model evaluation methodology changes (except using an existing offline gate as a cutover check)
- External API redesign or versioning programs
- Infrastructure provider replacement or multi-cloud moves
- Database schema redesign unrelated to architectural ownership
- New product feature development
- Implementation planning, coding tasks, sprint breakdowns, or file-level guidance
- Physical package/folder/layout design

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Architect Resolves Ownership Without Reading Code (Priority: P1)

A platform architect determines, from this plan alone, which concerns a capability requires, who owns each concern, which contracts are canonical, and what dependencies are allowed — without inspecting implementations.

**Why this priority**: If ownership requires code archaeology, governance has already failed.

**Independent Test**: For any in-scope production concern, a reviewer names Owner, Consumers, and lifecycle state using only this document and referenced ADRs/Principles.

**Acceptance Scenarios**:

1. **Given** a production capability, **When** a reviewer reads Canonical Architecture for that capability, **Then** they can list required concerns, required contracts, and forbidden dependencies without assuming a fixed stage order.
2. **Given** two historical implementations of one concern, **When** disposition and owner selection criteria are applied, **Then** exactly one Active Production Owner results.

---

### User Story 2 - Maintainer Retires Parallel Paths Safely (Priority: P1)

A maintainer sees migration phases, compatibility windows, and validation gates so retiring a parallel implementation cannot silently break production.

**Why this priority**: Premature retirement is the highest operational risk during consolidation.

**Independent Test**: Every Retire After Cutover concern has a predecessor phase and a sole-owner validation gate.

**Acceptance Scenarios**:

1. **Given** a concern marked Retire After Cutover, **When** migration order is checked, **Then** cutover and validation precede retirement.
2. **Given** mid-migration rollback need, **When** Compatibility Strategy is applied, **Then** the prior sole path can be restored until final retirement.

---

### User Story 3 - Domain Author Extends Without Capturing Core (Priority: P1)

A domain-pack author extends vertical behavior through Domain Packs and published extension contracts — not by becoming a second owner of core orchestration.

**Why this priority**: Generic architecture collapses if verticals capture core.

**Independent Test**: Ownership Rules forbid Domain Packs from owning core orchestration; Governance requires pack changes to reuse canonical contracts.

**Acceptance Scenarios**:

1. **Given** a new domain pack, **When** governance rules are followed, **Then** core concern ownership does not change.
2. **Given** domain-specific rules today living in core, **When** disposition completes, **Then** Domain Packs own those rules (or an ADR records a temporary exception).

---

### User Story 4 - Governance Prevents Future Drift (Priority: P2)

A reviewer evaluating a future change can accept or reject it using Principles, Invariants, Anti-Patterns, and Governance — without reopening consolidation.

**Why this priority**: Consolidation value is lost if drift returns.

**Independent Test**: A hypothetical “second production retrieval path” is rejectable by citing an Anti-Pattern and Governance rule.

**Acceptance Scenarios**:

1. **Given** a proposal that adds a parallel production path, **When** Architecture Governance is applied, **Then** the proposal is rejected unless an ADR supersedes the rule.
2. **Given** a lifecycle or ownership change, **When** the change lands, **Then** documentation and ADR/lifecycle status are required updates.

---

### Edge Cases

- Dual-run still active → Transitional Diagnostic only; retirement blocked until sole user-visible owner exists.
- Built capability with no consumer → Activation Pending Consumer, Dormant, or Research — never production-complete by implication.
- Answer consolidated, search not → Allowed with explicit interim ownership; undocumented third path forbidden.
- Competing contracts → One canonical contract; others lose production status after consumer migration.
- “Temporary” migration flags still selecting paths after sole-owner declaration → Forbidden Pattern; must retire or be re-justified by ADR.

---

## Architecture Principles

Governing rules for consolidation and future evolution. Exceptions require an ADR that explicitly supersedes the conflicting principle.

| ID | Principle | Meaning |
|----|-----------|---------|
| **P1** | One Concern = One Owner | Exactly one accountable owner per concern. Contributors and consumers are allowed; co-owners are not. |
| **P2** | One Production Path per Capability | Each capability has exactly one production execution path. |
| **P3** | One Canonical Contract per Concept | Shared concepts have exactly one production contract family. |
| **P4** | No Parallel Production Implementations | At most one implementation serves production for a concern. Dual-run is diagnostic only. |
| **P5** | Dependency Direction Inward Only | Outer layers may depend inward; inner layers MUST NOT depend on outer concretes. |
| **P6** | Composition Owns Wiring | Only Composition binds interfaces to infrastructure and selects active implementations. |
| **P7** | Infrastructure Behind Interfaces | Providers are reached only through interfaces. |
| **P8** | Domain Packs Extend Without Capturing Core | Domain rules live in packs; core orchestration stays domain-agnostic. |
| **P9** | Architecture Before Implementation | Ownership, contracts, and boundaries are decided before coding. Layout is non-normative. |
| **P10** | Lifecycle Honesty | Non-production capabilities use accurate lifecycle labels. |
| **P11** | Cutover Before Retirement | Ownership and traffic move first; retirement follows validation. |
| **P12** | Generic Platform Default | No vertical becomes permanent core behavior. |
| **P13** | Governance Over Inventory | Architecture specs define rules; detailed component catalogs live in implementation docs. |
| **P14** | Orchestration Is Not Identity | A capability is defined by concerns, contracts, and ownership — not by a single prescribed stage sequence — unless a specific ordering is recorded as an invariant or ADR. |

---

## Architecture Invariants

Permanent constraints. Violation means architectural failure until corrected.

| ID | Invariant |
|----|-----------|
| **I1** | Exactly one production execution path exists per in-scope capability. |
| **I2** | Exactly one Active Production Owner exists per production concern. |
| **I3** | Every production dependency resolves deterministically to one authoritative implementation. |
| **I4** | Infrastructure never owns business orchestration. |
| **I5** | Domain packs never own or modify core orchestration control flow. |
| **I6** | Every non-canonical or retiring implementation has an explicit lifecycle strategy. |
| **I7** | Duplicate ownership of the same concern is forbidden. |
| **I8** | Core concerns never depend on concrete infrastructure providers. |
| **I9** | Presentation never owns pipeline algorithms. |
| **I10** | Dual-run/diagnostic paths never become the user-visible response owner. |
| **I11** | Offline evaluation never sits on the production request path. |
| **I12** | A capability without a declared production consumer is not an active production stage. |
| **I13** | No undocumented production path exists. |
| **I14** | Architectural decisions that select among alternatives are traceable to an ADR; standing rules are traceable to a Principle or Invariant. |

---

## Forbidden Architecture Patterns

These patterns are **prohibited** unless an approved ADR explicitly supersedes the relevant rule for a bounded scope and duration.

| ID | Anti-Pattern | Why it is forbidden |
|----|--------------|---------------------|
| **AP1** | Parallel production implementations | Breaks P2/P4; doubles drift surface |
| **AP2** | Duplicate canonical contracts for one concept | Breaks P3; forces adapter sprawl |
| **AP3** | Multiple owners for the same concern | Breaks P1/I7; decision deadlock |
| **AP4** | Business orchestration inside infrastructure | Breaks I4; traps logic in providers |
| **AP5** | Domain logic inside Composition | Captures verticals in wiring; fights P8 |
| **AP6** | Core depending on concrete infrastructure | Breaks P5/P7/I8 |
| **AP7** | Pipeline bypasses that skip owned concerns while claiming the capability | Hidden incomplete path; violates I13 |
| **AP8** | Feature flags as permanent architecture | Flags are transition tools, not ownership |
| **AP9** | Temporary migration code becoming permanent | Institutionalizes dual-path debt |
| **AP10** | Hidden production paths | Violates I13; defeats governance |
| **AP11** | Duplicate lifecycle ownership (“both active and pending”) | Makes status non-deterministic |
| **AP12** | Owner chosen by age, folder, or historical package name | Violates Owner Selection Criteria |
| **AP13** | Treating inactive capabilities as production-complete in docs | Violates P10/I12 |
| **AP14** | Prescribing implementation layout as architecture | Couples governance to accidents of structure |

---

## Architecture Governance

Rules for **future evolution**. Consolidation is complete only if these remain enforceable afterward.

### Every new or changed capability MUST

1. Identify a single concern Owner before merge to production.
2. Reuse canonical contracts for shared concepts; propose a contract change via ADR if reuse is impossible.
3. Respect dependency direction (P5) and Composition-owned wiring (P6).
4. Avoid duplicate ownership (P1) and parallel production paths (P2/P4).
5. Declare lifecycle state for any non-production or transitional implementation.
6. Update ADRs when an architectural tradeoff decision changes.
7. Update lifecycle/ownership records when ownership changes.
8. Pass Architecture Validation before claiming production readiness.

### Every retirement MUST

1. Demonstrate a sole Active Production Owner for the concern.
2. Demonstrate zero production consumers of the retiree.
3. Preserve rollback capability until the retirement gate passes.
4. Remove or relabel transitional diagnostics so they cannot become hidden paths.

### Review obligations

- Architecture review rejects changes that match Forbidden Patterns without a superseding ADR.
- “Exception” ADRs MUST state scope, duration, and exit criteria.
- Implementation documentation may hold detailed ownership inventories; this specification remains the governance source of truth.

---

## Architecture Decisions

Intentional consolidation choices. Standing philosophy lives in Principles; only tradeoffs are expanded as ADRs.

| ID | Decision | Authority |
|----|----------|-----------|
| **D1** | Migration target is a unified single production path per capability | ADR-001 |
| **D2** | Answer consolidation precedes search consolidation | ADR-002 |
| **D3** | External answer API contract remains frozen during consolidation | ADR-003 |
| **D4** | Structured knowledge stays off the active production path until a consumer is declared | ADR-004 |
| **D5** | Offline evaluation remains a cutover quality gate, not a runtime stage | P / I11 (no ADR — not a contested alternative set for this plan) |
| **D6** | Physical layout and concrete type names are non-normative | P3, P9, P14 |
| **D7** | Re-indexing is an accepted compatibility event when sole chunking/embed-text policy changes materially | Compatibility Strategy |
| **D8** | This artifact is architecture/governance only | Scope / FR-001 |

---

## Architecture Decision Records

An ADR exists only when: there is a real architectural problem, multiple valid alternatives existed, one option was intentionally selected, and tradeoffs are documented. Principle restatements are not ADRs.

### ADR-001 — Unified Single Path as Migration Target

- **Context**: Production and parallel stage-oriented stacks coexisted, creating duplicated ownership and false completeness claims.
- **Decision**: Consolidate to one production path per capability; dual-run is transitional diagnostic only.
- **Alternatives considered**: (A) Permanent dual stacks with parity mandates; (B) Standardize on the legacy path and abandon the parallel stack; (C) Unified single path with phased cutover.
- **Tradeoffs**: (A) permanent complexity; (B) may discard valuable stage contracts; (C) higher near-term migration cost, lower long-term drift — chosen.

### ADR-002 — Answer Consolidation Before Search

- **Context**: Answer and search both consume retrieval but differ in API risk and cutover blast radius.
- **Decision**: Achieve answer sole ownership first; move search onto the same canonical retrieval owner afterward.
- **Alternatives considered**: (A) Simultaneous cutover; (B) Search-first; (C) Answer-first.
- **Tradeoffs**: Temporary explicit interim search ownership vs. safer sequencing — (C) chosen. Undocumented divergence remains forbidden (I13).

### ADR-003 — Frozen External Answer Contract During Consolidation

- **Context**: Clients depend on a stable external answer shape while internals consolidate.
- **Decision**: Freeze the external answer contract for the consolidation window; adaptation stays in Application.
- **Alternatives considered**: (A) Evolve API with internal stages; (B) Freeze; (C) Ship parallel versioned APIs.
- **Tradeoffs**: (B) constrains internal representation at the edge but avoids client breakage and scope creep into API redesign — chosen.

### ADR-004 — Knowledge Off Active Path Until Consumer Exists

- **Context**: A knowledge capability may exist without a production consumer, creating maintenance and documentation drift.
- **Decision**: Keep it Activation Pending Consumer (or Research Capability if no consumer is planned). Do not block sole-path consolidation on activation.
- **Alternatives considered**: (A) Force immediate wiring; (B) Delete immediately; (C) Lifecycle-classify and sequence separately.
- **Tradeoffs**: Deferred product value vs. unblocked consolidation and honest lifecycle — (C) chosen.

---

## Canonical Architecture

Architecture defines **required concerns, contracts, ownership, and dependency rules**. It does **not** prescribe a single mandatory orchestration sequence unless ordering is stated as an invariant or ADR.

Per **P14**, any orchestration that satisfies a capability’s required concerns, contracts, ownership, and dependency rules is architecturally valid.

### Logical layers (dependency vocabulary)

| Layer | Role |
|-------|------|
| Presentation | External interaction contracts |
| Composition | Wiring and active-implementation selection |
| Application | Use-case facades; adaptation to external contracts |
| Core Concerns | Domain/application stage logic behind interfaces |
| Infrastructure | Provider and persistence implementations |
| Domain Packs & Configuration | Extensibility without capturing core |

### Capability: Answer

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Turn an authorized user question into a grounded answer under the frozen external contract |
| **Required Concerns** | Query understanding; retrieval planning; retrieval execution; evidence organization; context assembly; answer generation; external response adaptation; composition/wiring |
| **Required Contracts** | One canonical contract family each for: understood query, retrieval plan intent, retrieval results, evidence set, assembled context, generated answer, external answer response |
| **Ownership** | Each required concern has exactly one Owner (see Ownership Rules). Adaptation is Application-owned; wiring is Composition-owned |
| **Allowed Dependencies** | Presentation → Application/Composition; Application → Core concern interfaces + Domain Pack profiles; Core → peer contracts + injected pack profiles; Composition → all layers for wiring only; Core → Infrastructure **interfaces only** |
| **Forbidden Dependencies** | Core → concrete infrastructure; Infrastructure → orchestration ownership; Domain Packs → core control flow; Presentation → core algorithms; second production path for Answer |

*Ordering note*: Natural data dependencies may constrain feasible orchestrations (e.g. generation consumes context). Those are contract dependencies, not a mandated global pipeline diagram.

### Capability: Ingest

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Turn authorized content into durable, retrievable indexed knowledge units |
| **Required Concerns** | Document parsing; chunking (including sole embed-text policy); persist & index; ingest orchestration; composition/wiring |
| **Required Contracts** | One canonical contract family each for: parsed document, chunk set / indexable units, persistence acknowledgment |
| **Ownership** | Parse, chunking, and ingest orchestration each have one Owner; infrastructure owns provider persistence implementations |
| **Allowed Dependencies** | Application ingest orchestration → parse/chunk interfaces → infrastructure persistence interfaces; Domain Packs may supply parse/chunk profiles via injection |
| **Forbidden Dependencies** | Multiple production chunking entrypoints; infrastructure-owned chunk policy; domain packs owning ingest control flow; knowledge concern on the path unless Active Production |

**Optional concern**: Structured knowledge — only when lifecycle is Active Production with a declared consumer (ADR-004).

### Capability: Search

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Return ranked retrievable units for an authorized query without answer generation |
| **Required Concerns** | Query intake (as needed); retrieval execution; search response adaptation; composition/wiring |
| **Required Contracts** | Reuse canonical retrieval-result contract; one external search response contract |
| **Ownership** | After consolidation: same retrieval-execution Owner as Answer. Until then: explicit interim Owner documented (ADR-002) |
| **Allowed Dependencies** | Presentation → Application → retrieval interfaces; Composition wiring |
| **Forbidden Dependencies** | Undocumented retrieval stack divergent from stated owner; silent semantic change without validation gate |

### Capability: Offline Evaluation

| Dimension | Definition |
|-----------|------------|
| **Purpose** | Measure answer/retrieval quality offline for release and cutover decisions |
| **Required Concerns** | Evaluation orchestration; scoring; reporting |
| **Required Contracts** | Evaluation suite input/output contracts distinct from runtime answer contracts |
| **Ownership** | Single Owner for offline evaluation capability |
| **Allowed Dependencies** | May invoke production concerns in non-production environments through published interfaces |
| **Forbidden Dependencies** | Presence on production request path (I11); replacing architecture decisions with metric gaming |

### Cross-cutting contract rules

- One canonical contract per shared concept in production.
- Stages/concerns publish interfaces; they do not fork parallel production shapes for the same concept.
- External API adaptation occurs in Application, not inside core concerns.
- Cross-cutting signals that multiple concerns must honor (e.g. citation lineage, degradation) belong in contracts, not side channels with competing owners.

---

## Ownership Model

Governance-first. Detailed component inventories belong in implementation documentation (P13).

### Ownership Rules

1. Every production concern has exactly one **Owner**.
2. **Contributors** may change internals only with Owner accountability; contribution ≠ ownership.
3. **Consumers** depend only on the Owner’s published contracts/interfaces.
4. A party may Own one concern and Consume another.
5. Ownership disputes are resolved by Owner Selection Criteria, not by history or layout.
6. Lifecycle state is part of ownership truthfulness (P10).

### Ownership Responsibilities

| Role | Responsibilities |
|------|------------------|
| **Owner** | Contract integrity; sole production implementation authority; approve contributors; maintain lifecycle honesty; ensure dependency rules; participate in retirement gates |
| **Contributor** | Implement under Owner direction; no parallel production fork; no covert contract changes |
| **Consumer** | Use published contracts only; report contract gaps; do not re-implement the owned concern |
| **Composition** | Wire the Owner’s implementation as the active production binding; never silently bind a second owner |
| **Architecture governance** | Enforce Principles, Invariants, Anti-Patterns; require ADRs for tradeoff changes |

### Representative examples (non-catalog)

| Concern (example) | Owner (logical) | Typical Contributors | Typical Consumers |
|-------------------|-----------------|----------------------|-------------------|
| Retrieval execution | Canonical Retrieval Owner | Infrastructure adapter authors | Evidence, Search, Answer application facade |
| Chunking & embed-text policy | Canonical Chunking Owner | Pack profile authors (injected) | Persist & index; retrieval data plane |
| External answer adaptation | Application (Answer) | — | Presentation / clients |
| Provider wiring & path selection | Composition | Registration helpers | All runtime entrypoints |
| Domain vocabulary / vertical heuristics | Domain Packs | Vertical authors | Query understanding, planning, chunking via injection |
| Offline evaluation | Offline Evaluation Owner | Metric contributors | Release/cutover process |

---

## Owner Selection Criteria

Used when establishing or changing an Active Production Owner for a concern.

### Select the Canonical Owner by

| Criterion | Meaning |
|-----------|---------|
| **Architectural alignment** | Fits layer rules, dependency direction, and concern boundaries |
| **Production maturity** | Fit for production responsibility (completeness of concern, not demo isolation) |
| **Operational stability** | Operable under real load, failure, and observability expectations for that concern |
| **Validation results** | Passes required Architecture/Code/Runtime/Operational gates for the cutover |
| **Extensibility** | Supports Domain Packs and provider substitution without ownership capture |
| **Maintainability** | Clear contracts, testable behind interfaces, low accidental coupling |

### Never select the Canonical Owner by

- Implementation age (“newer” or “older”)
- Historical ownership alone
- Folder structure or package/directory names
- Convenience of the current caller graph without meeting criteria above
- Presence of feature flags or migration shims

Selection outcomes SHOULD be recorded when they resolve a contested choice (ADR if alternatives were genuinely competing at decision time).

---

## Concern Disposition

### Lifecycle vocabulary

| State | Meaning |
|-------|---------|
| **Active Production Owner** | Sole production implementation for the concern |
| **Consolidate Into Owner** | Responsibility merges into the Active Production Owner |
| **Retire After Cutover** | Remove/archive only after sole owner + gates |
| **Activation Pending Consumer** | Intentionally unused until a production consumer is declared |
| **Dormant Capability** | Intentionally unused; may activate later under a new decision |
| **Research Capability** | Exploratory; not a production dependency |
| **Transitional Diagnostic** | Dual-run/comparison only; never user-visible owner |

### Disposition strategy (concern-level)

| Situation | Disposition |
|-----------|-------------|
| Competing production implementations of one concern | One Active Production Owner via Owner Selection Criteria; others Consolidate or Retire After Cutover |
| Duplicate contracts for one concept | One canonical contract; retire competitors after consumer migration |
| Dual-run / shadow tooling | Transitional Diagnostic → Retire After Cutover (or offline-only under Evaluation Owner) |
| Built capability, no consumer | Activation Pending Consumer / Dormant / Research (ADR-004 pattern) |
| Domain rules in core | Consolidate Into Domain Pack ownership |
| Dead unreachable alternate logic | Retire After Cutover (no feature replacement implied) |

### Convergence sequence

1. Name the concern and required contracts.
2. Select Active Production Owner using Owner Selection Criteria.
3. Cut over consumers to the owner’s contracts.
4. Validate sole ownership (four validation categories).
5. Retire competitors and transitional diagnostics.
6. Update lifecycle records; add/amend ADR if a tradeoff decision changed.

---

## Migration Order

Architectural phases, not implementation tickets. Later phases MUST NOT retire competitors before exit gates pass.

| Phase | Name | Outcome | Exit gate |
|-------|------|---------|-----------|
| **M0** | Freeze dual-path growth | No new parallel production implementations | Freeze accepted; dual-path labeled transitional |
| **M1** | Answer sole owner | One user-visible Answer path | Quality gate vs baseline; deterministic path selection; I13 holds |
| **M2** | Retrieval sole owner | One retrieval-execution Owner for Answer; Search interim ownership explicit | Deterministic retrieval dependency; parity or accepted deltas recorded |
| **M3** | Contract unification | One production contract per shared concept | No duplicate production contracts |
| **M4** | Ingest/chunking sole path | One parse→chunk production ownership model; one embed-text policy owner | Critical ingest validation; policy stability |
| **M5** | Dependency direction | Core free of concrete infrastructure dependencies | Boundary validation |
| **M6** | Domain extraction | Vertical heuristics owned by Domain Packs | Pack enablement without core ownership change |
| **M7** | Retirement wave | Retire After Cutover + transitional diagnostics cleared from production | Zero production consumers of retirees |
| **M8** | Lifecycle resolution | Pending/Dormant/Research honestly labeled, activated, or archived | Docs match lifecycle truth |

---

## Compatibility Strategy

| Concern | Strategy |
|---------|----------|
| External answer API | Frozen (ADR-003); Application adaptation only |
| Operator cutover | Composition-controlled selection; sole-path before retirement |
| Rollback before M7 | Restore prior selection / prior release |
| Rollback after M7 | Redeploy prior release artifact |
| Search | Explicit interim owner until ADR-002 follow-through |
| Indexed corpus | Re-index when sole embed-text/chunk policy changes materially (D7) |
| Domain packs | Prefer additive changes; breaking keys need migration notes |
| Offline evaluation | Cutover gate only; not runtime |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Retiring still-serving path | Outage | P11; consumer validation |
| Isolation-green, production-weak owner | Quality regression | Owner Selection Criteria + Runtime/Operational gates |
| Dual-run mistaken for sole-path | False confidence | I10; AP8/AP9 |
| Embed-text unify without re-index | Silent skew | D7 |
| Domain extraction incomplete | Vertical regression | Pack ownership before core removal |
| Lifecycle mislabeling | Drift returns | P10; Governance; M8 |
| Spec becomes component catalog | Unmaintainable governance | P13; lean Ownership Model |
| Orchestration prescription locks design | Accidental rigidity | P14; capability cards |

---

## Validation

### Architecture Validation

- **V-A1**: Each in-scope capability has Purpose, Required Concerns, Required Contracts, Ownership, Allowed/Forbidden Dependencies.
- **V-A2**: Exactly one Active Production Owner per production concern.
- **V-A3**: No Forbidden Pattern present without superseding ADR.
- **V-A4**: Dependency rules show no inward violations.
- **V-A5**: Every Architecture Decision maps to an ADR or Principle/Invariant (I14).
- **V-A6**: Lifecycle labels are honest for non-production capabilities.
- **V-A7**: No ownership determination requires implementation inspection (process check via review).

### Code Validation

- **V-C1**: Production wiring selects one implementation per concern.
- **V-C2**: Core concerns do not depend on concrete infrastructure.
- **V-C3**: Retired concerns have zero production consumers.
- **V-C4**: Domain orchestration is not owned by core.
- **V-C5**: No duplicate production contracts for the same concept after M3.
- **V-C6**: External answer contract tests remain green.
- **V-C7**: No hidden production entrypoints (I13).

### Runtime Validation

- **V-R1**: Answer cutover quality gate within agreed tolerance at M1.
- **V-R2**: Critical ingest yields retrievable content after M4.
- **V-R3**: Retrieval dependency behaves per accepted parity/delta record after M2.
- **V-R4**: Diagnostics never observed as user-visible owner after M1.

### Operational Validation

- **V-O1**: Serving owner/path observable until sole-path; correlation remains after.
- **V-O2**: Soak thresholds met before retirement.
- **V-O3**: Rollback verified before each retirement wave.
- **V-O4**: Docs match ownership and lifecycle after M7–M8.
- **V-O5**: Re-index completed or explicitly waived with recorded risk when policy changes.

### Process Validation

- **V-P1**: No implementation tasks in this specification.
- **V-P2**: Out of Scope items were not smuggled into consolidation acceptance.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: This artifact MUST remain an architecture/governance plan only — no implementation task lists.
- **FR-002**: The plan MUST define principles, invariants, anti-patterns, governance, decisions/ADRs, capability architecture (concerns/contracts/ownership/dependencies), ownership rules, owner selection criteria, disposition, migration order, compatibility, risks, and validation.
- **FR-003**: Consolidation MUST preserve pack-extensible generic architecture (P8, P12).
- **FR-004**: Each in-scope capability MUST be specified by Purpose, Required Concerns, Required Contracts, Ownership, Allowed Dependencies, and Forbidden Dependencies — not by a mandatory global stage sequence (P14).
- **FR-005**: Production MUST converge to one Answer path and one Ingest path under those capability definitions.
- **FR-006**: Retrieval execution MUST have one Active Production Owner for Answer after M2; Search MUST share that owner after its phase (ADR-002).
- **FR-007**: Chunking MUST have one Active Production Owner and one embed-text policy authority after M4.
- **FR-008**: One canonical contract per shared concept; one published interface authority per production concern role.
- **FR-009**: Dependency direction MUST follow Canonical Architecture rules (P5–P7).
- **FR-010**: Ownership Model MUST define rules, responsibilities, and representative examples — not a full component catalog (P13).
- **FR-011**: Owner selection MUST follow Owner Selection Criteria; AP12 is forbidden.
- **FR-012**: Competing concerns MUST be dispositioned with lifecycle vocabulary; inactive capabilities MUST NOT be labeled production-complete.
- **FR-013**: Migration MUST cut over before retirement (P11).
- **FR-014**: Dual-run MUST remain Transitional Diagnostic only (I10).
- **FR-015**: External answer contract remains frozen during consolidation (ADR-003) unless a separate API specification supersedes it.
- **FR-016**: Validation MUST cover Architecture, Code, Runtime, and Operational categories.
- **FR-017**: Future changes MUST comply with Architecture Governance or an explicit superseding ADR.

### Key Entities

- **Capability**: Cohesive production purpose (Answer, Ingest, Search, Offline Evaluation)
- **Concern**: Single responsibility with exactly one Owner
- **Canonical Contract**: Sole production contract family for a concept
- **Owner / Contributor / Consumer**: Governance roles
- **Lifecycle State**: Production or non-production status vocabulary
- **Composition**: Sole wiring authority
- **Domain Pack**: Vertical extension that must not capture core
- **ADR**: Record of a contested architectural tradeoff
- **Validation Gate**: Exit criterion for a migration phase

### Non-Functional Requirements

- **NFR-001**: Strengthen layering and dependency inversion.
- **NFR-002**: Preserve provider substitutability via interfaces.
- **NFR-003**: Where enabled, hybrid retrieval, reranking, citations, and prompt versioning remain properties of the canonical Answer capability — not parallel shadow ownership.
- **NFR-004**: Preserve generic pack extensibility.
- **NFR-005**: Observability of serving owner until sole-path; correlation thereafter.
- **NFR-006**: No secrets in architecture artifacts.
- **NFR-007**: Later implementation of this plan follows normal testing discipline; this artifact is review-gated.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No in-scope production concern requires implementation inspection to determine ownership.
- **SC-002**: Every production concern maps to exactly one Owner.
- **SC-003**: Every production dependency resolves deterministically (no production either/or).
- **SC-004**: No undocumented production path exists.
- **SC-005**: Every architectural decision is traceable to an ADR or Principle/Invariant (I14).
- **SC-006**: Zero competing production implementations for Answer after M1.
- **SC-007**: Zero competing production implementations for Chunking after M4.
- **SC-008**: Zero duplicated ownership across production concerns.
- **SC-009**: Zero Forbidden Patterns remain without a superseding ADR after M7.
- **SC-010**: Answer cutover quality gate within agreed tolerance at M1.
- **SC-011**: Lifecycle documentation matches Activation Pending / Dormant / Research truth (zero false production-complete claims).
- **SC-012**: A reviewer can reject a parallel-path proposal using only Governance + Anti-Patterns in under five minutes.

---

## Assumptions

External constraints or unknowns — not architecture choices.

- An existing or in-flight answer cutover mechanism (diagnostic dual-run → sole path) will be reused; this plan does not define a competing cutover product.
- Clients depend on the current external answer API shape during consolidation.
- Numeric soak/fallback thresholds may be set in operational runbooks without changing sole-path intent.
- At least one real domain pack will exercise pack-based extension during domain extraction.
- Platform constitution/governance documents remain external authorities alongside this plan.
- Validity of this plan MUST NOT depend on today’s source layout or type names.

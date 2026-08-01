# Contract: Compatibility with Features 014–018

**Feature**: 019-rag-evaluation-framework | **Version**: 1.0.0

Normative compatibility so evaluation architecture cannot violate existing Spec Kit features.

---

## Purpose

Preserve metric semantic continuity, cutover vehicle, sole-owner governance, quality-stage contracts, and evaluation non-ownership of production paths.

---

## Feature 014 — Answer Quality

| Rule | Requirement |
|------|-------------|
| Semantic continuity | Coverage / Faithfulness / Completeness semantics remain valid |
| Architecture authority | **019** becomes evaluation architecture authority (modes, profiles, ownership, monitoring, governance) |
| Extension not discard | 014 golden/regression concepts are extended into the broader framework |
| Feedback | Offline evaluation remains the configuration feedback source posture for quality loops |

---

## Feature 015 — Unified Pipeline Migration

| Rule | Requirement |
|------|-------------|
| Dual-run / shadow inputs | Allowed as experiment/shadow evaluation subjects |
| No second owner | Evaluation MUST NOT become a second production answer owner |
| Frozen external API | 019 MUST NOT require redesign of frozen external `/answer` fields |
| Skip not PASS | Unavailable shadow path ⇒ explicit SKIP, never silent PASS |

---

## Feature 016 — Architecture Consolidation

| Rule | Requirement |
|------|-------------|
| Sole owner | Metric Primary Owners map to existing production concerns; no new production stages |
| M0 freeze | No parallel production retrieval/answer implementations for “evaluation mode” |
| Non-production path | Evaluation is offline / CI / shadow / monitoring only |
| Ops attribution | Latency/Cost “Whole Pipeline” ownership is evaluation attribution only |

---

## Feature 018 — RAG Quality Architecture

| Rule | Requirement |
|------|-------------|
| Diagnostics | 018 stage metrics remain diagnostic / offline-alignable |
| Gate precedence | On release/cutover disagreement, **019 gates win** over 018 heuristics |
| Trace reuse | Prefer Quality Context / Quality Trace enrichment |
| No sixth owner | 019 does not create a production “quality” stage owner |
| Feedback loop | Offline feedback loop continues; 019 widens evaluation surface feeding that loop |

---

## Feature 017 — Scalability & Reliability (orthogonal)

| Rule | Requirement |
|------|-------------|
| Orthogonality | 017 ingest reliability remains orthogonal |
| No coupling | Evaluation contracts MUST NOT depend on ingest job control-plane entities |
| Future subject | Ingest quality may later appear as an evaluation subject without changing ingest ownership |

---

## Acceptance

Architecture review fails if 019 design:

- Redefines 014 Faithfulness/Completeness incompatibly
- Creates a parallel production answer/retrieval path
- Reassigns 016 sole owners or adds a production evaluation stage
- Lets 018 diagnostics override 019 release gates
- Requires frozen external answer API redesign
)

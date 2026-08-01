# Contract: Dependency Boundaries

**Feature**: 016-architecture-consolidation | **Version**: 1.0.0

Normative allowed and forbidden dependency directions between logical layers.

---

## Layer Vocabulary

| Layer | Meaning |
|-------|---------|
| Presentation | External interaction |
| Composition | Wiring + active implementation selection |
| Application | Use-case facades + external contract adaptation |
| Core Concerns | Stage/domain logic behind interfaces |
| Infrastructure | Provider and persistence implementations |
| Domain Packs & Configuration | Extensibility profiles |

---

## Allowed Matrix

| From → To | Presentation | Composition | Application | Core | Infrastructure | Domain Packs |
|-----------|--------------|-------------|-------------|------|----------------|--------------|
| Presentation | — | Yes | Yes | No | No | No |
| Composition | No | — | Yes | Yes | Yes | Yes |
| Application | No | No | — | Yes | Yes (interfaces/adapters) | Yes |
| Core | No | No | No | Peer contracts only | **Interfaces only** | Injected profiles only |
| Infrastructure | No | No | No | Implements interfaces | — | No |
| Domain Packs | No | Consumed | Consumed | Consumed via injection | No | — |

---

## Forbidden (normative)

- Core → concrete infrastructure providers
- Infrastructure owns business orchestration
- Domain Packs modify core control flow
- Presentation embeds pipeline algorithms
- Composition embeds domain heuristics (beyond wiring/selection)
- Any production consumer depending on a non-owner’s private shapes for a shared concept

---

## Composition Exclusivity

Only Composition may:

1. Bind interface → active implementation for production
2. Select path/mode during transitional periods
3. Register provider factories for runtime use

Application MAY offer registration helpers; it MUST NOT silently bind a second Active Production Owner.

---

## Contract Dependencies vs Orchestration Order

Concerns may declare **contract dependencies** (e.g. generated answer requires assembled context). Those constraints limit feasible orchestrations but do **not** redefine layer dependency rules and do **not** themselves mandate a single global pipeline diagram.

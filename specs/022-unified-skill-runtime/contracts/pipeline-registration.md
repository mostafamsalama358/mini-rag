# Contract: Declarative Pipeline Registration

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Required composition model

```text
PipelineBuilder
  → register(stage)…
  → build()
  → Orchestrator.execute(chain, context)
```

## Rules

1. Adding a stage MUST NOT require editing orchestrator **core logic** (registration/composition only).
2. Skill-bound and non-Skill chains MAY share builder machinery with different registrations.
3. Future registrable stages (surfaces; not all required to ship): Clarification, Safety, Guardrails, Tool Invocation, Post Validation, Citation Enforcement, Prompt Resolution, Reranking, …

## God-object elimination

Target ownership:

```text
Request → Skill Resolver → Pipeline Orchestrator → Stages → Response
```

`answer_service` MUST NOT remain the Skill orchestration owner at completion.

## Acceptance

- Quickstart / test demonstrates registering an extra no-op stage without modifying orchestrator internals.
- Architecture or unit proof that Skill path uses builder-registered chain.

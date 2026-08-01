# Contract: Pipeline Stage Contracts

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Every stage MUST declare

| Element | Requirement |
|---------|-------------|
| Input | Explicit types / prior results consumed |
| Output | Immutable StageResult |
| Failure conditions | Clarification, abort, no-context, transport/LLM errors as applicable |
| Side effects | Documented (DB/LLM/metrics) or none |

## Communication rules

- Stages communicate **only** through immutable objects.
- Stages MUST NOT mutate outputs produced by previous stages.
- Stages MUST NOT mutate `SkillExecutionContext`.
- Each stage MUST be independently testable against its contract.

## Minimum Skill stages (022)

1. Validation  
2. Entity Parsing  
3. Retrieval (via StrategyRegistry)  
4. Generation  
5. Formatting  

Reranking / prompt resolution MAY be distinct registered stages or explicit substeps with contracts.

## Acceptance

- Unit tests exist per minimum stage.
- Architecture/immutability tests cover non-mutation.

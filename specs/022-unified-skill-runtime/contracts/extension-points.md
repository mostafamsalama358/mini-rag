# Contract: Extension Points

**Feature**: 022-unified-skill-runtime | **Date**: 2026-07-28

---

## Principle

New extensions SHOULD require **registration only**—no shared-engine edits.

## Workflow stages (surfaces)

- Validation  
- Clarification  
- Safety  
- Guardrails  
- Tool Invocation  
- Formatter  
- Citation Enforcement  
- (also Entity Parsing, Retrieval, Reranking, Prompt Resolution, Generation, Post Validation as applicable)

## Retrieval strategies (surfaces)

Mandatory in 022: `default`, `semantic_only`, `hybrid`, `document_lookup`, `pair_lookup`

Optional catalog examples: `keyword_only`, `graph`, …

## Response formatters (surfaces)

Examples: `markdown`, `json`, `clinical`, `citation_only`

Shipping every listed formatter is **not** required for 022 completion; the registration surface must exist or be designed so formatters can register without engine edits.

## Acceptance

- Extension points documented here and referenced from plan/quickstart.
- At least Strategy Registry + PipelineBuilder prove registration-only extension for stages/strategies.

"""Architectural stage contract assertions (contracts/stage-contracts.md)."""

from __future__ import annotations

STAGE_CONTRACTS: dict[str, dict[str, str]] = {
    "admission_validation": {
        "accepted_input": "submission intent + tenant + content reference",
        "produced_output": "Accepted/Validating job with capacity claim",
        "failure": "security/policy/capacity reject; no expensive work",
        "completion": "eligible for Parsing",
    },
    "parsing": {
        "accepted_input": "validated content reference + budgets",
        "produced_output": "Document Model + parse outcome",
        "failure": "failed parse / dependency unavailable",
        "completion": "Chunk Preparation if min-content gate passes",
    },
    "chunk_preparation": {
        "accepted_input": "Document Model passing post-parse gates",
        "produced_output": "bounded unpublished chunk units",
        "failure": "budget/structural failure",
        "completion": "ready for Enrichment",
    },
    "enrichment": {
        "accepted_input": "prepared chunk units",
        "produced_output": "enriched unpublished batches",
        "failure": "dependency/circuit fail-fast",
        "completion": "ready for Indexing",
    },
    "indexing": {
        "accepted_input": "enriched unpublished batches",
        "produced_output": "index materialization not Active",
        "failure": "storage/db issues",
        "completion": "ready for Publishing gates",
    },
    "publishing": {
        "accepted_input": "unpublished material + integrity evidence",
        "produced_output": "exactly-once PublishCompletion + Active Version",
        "failure": "integrity fail; Active unchanged",
        "completion": "Completed or Completed With Warnings",
    },
}


def assert_only_publishing_activates(stage: str) -> None:
    if stage != "publishing":
        raise AssertionError("Only publishing stage may activate Active Version")

# Contract: BoundaryDecisionPolicy Interface

**Feature**: `007-intelligent-chunking-engine` | **Date**: 2026-07-13

This contract defines the stable interface that every Boundary Decision Policy implementation
must satisfy. The `SemanticStructuralChunkingStrategy` depends only on this contract, not on
any concrete policy class.

---

## Interface Definition

**Location**: `src/core/chunking/interfaces.py`

```python
from typing import Protocol
from core.chunking.models import BoundaryCandidate, BoundaryFeatures, BoundaryDecision

class BoundaryDecisionPolicy(Protocol):
    """Stable interface for every Boundary Decision Policy implementation.

    Implementors:
    - Receive a BoundaryCandidate and its already-computed BoundaryFeatures.
    - MUST return exactly one BoundaryDecision per call.
    - MUST NOT compute BoundaryFeatures (that is SemanticBoundaryEvaluator's job).
    - MUST NOT construct, assemble, or mutate Chunk objects.
    - MUST NOT include probabilistic confidence scores in BoundaryDecision.
    - MUST be deterministic: same inputs → same BoundaryDecision every time.
    - MUST NOT make network calls, LLM calls, or any blocking I/O.
    """

    def decide(
        self,
        candidate: BoundaryCandidate,
        features: BoundaryFeatures,
    ) -> BoundaryDecision:
        """Decide merge or split for one boundary candidate.

        Args:
            candidate: The BoundaryCandidate describing the adjacent element pair.
            features: Pre-computed BoundaryFeatures for this candidate (do not re-compute).

        Returns:
            BoundaryDecision with decision, applied_rule, triggered_features, rationale.
            - decision: 'merge' or 'split' only.
            - triggered_features: non-empty, references only valid BoundaryFeatures fields.
            - No confidence score, no assembled Chunk, no probabilistic output.
        """
        ...
```

---

## Registration Contract

**Location**: `src/core/chunking/registry.py`

```python
def register_policy(name: str, cls: type[BoundaryDecisionPolicy]) -> None:
    """Register a policy class under the given name."""

def get_boundary_decision_policy(name: str) -> BoundaryDecisionPolicy:
    """Instantiate the policy registered under 'name'.

    Raises KeyError for unknown names.
    """
```

---

## Default Policy: RuleBasedBoundaryDecisionPolicy

**Name**: `"rule_based"` | **Location**: `src/core/chunking/strategies/semantic_structural.py`

Rule precedence (deterministic, research R1):

| Priority | Signal | Decision |
|---|---|---|
| 1 (highest) | `table_integrity=False` OR `code_integrity=False` OR `quote_integrity=False` | `split`, rule=`"structural_integrity"` |
| 2 | `section_continuity=False` | `split`, rule=`"section_boundary"` |
| 3 | `heading_continuity=False` AND `size_budget=within_limit` | `split`, rule=`"heading_boundary"` |
| 4 | `hierarchy_continuity=False` | `split`, rule=`"hierarchy_breach"` |
| 5 | `size_budget=over_limit` | `split`, rule=`"size_budget"` |
| 6 | `structural_compatibility=False` | `split`, rule=`"type_incompatibility"` |
| 7 | `layout_continuity=False` AND `lexical_continuity=False` | `split`, rule=`"layout_lexical_incompatibility"` |
| 8 (default) | all signals pass | `merge`, rule=`"default_merge"` |

`triggered_features` is always the specific BoundaryFeatures field(s) that fired the matching
rule. For rule 8, `triggered_features = []` is not allowed — use `["size_budget"]` (within limit
confirmed) as the tiebreaker confirmation.

---

## Invariants

1. `BoundaryDecision.decision` is always `"merge"` or `"split"` — no other value.
2. `BoundaryDecision.triggered_features` is non-empty and contains only valid `BoundaryFeatures` field names.
3. `BoundaryDecision` contains no numeric confidence or probability field (verified by `ChunkValidator` / SC-016).
4. The policy does not receive the Chunk Builder's state — it sees only the candidate and features.
5. Adding a new policy requires implementing this Protocol and calling `register_policy()` — zero changes to the evaluator, builder, or engine dispatch.

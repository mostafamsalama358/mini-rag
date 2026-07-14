"""Passthrough query expander — returns the original query as a single variant."""

from __future__ import annotations

from core.retrieval_engine.interfaces import IQueryExpander
from core.retrieval_engine.models import ExpansionContext, ExpansionResult


class PassthroughExpander(IQueryExpander):
    @property
    def expander_id(self) -> str:
        return "passthrough"

    @property
    def expansion_type(self) -> str:
        return "passthrough"

    def expand(self, context: ExpansionContext) -> ExpansionResult:
        return ExpansionResult(
            variants=(context.query_text,),
            expansion_type="passthrough",
            metadata={},
        )

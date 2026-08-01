"""Entity-hint query expander — adds entity-grounded retrieval variants."""

from __future__ import annotations

from core.retrieval_engine.interfaces import IQueryExpander
from core.retrieval_engine.models import ExpansionContext, ExpansionResult


class EntityHintExpander(IQueryExpander):
    """Keep the original query and add a compact entity-focused variant.

    Helps factual dosing/contraindication lookups where the natural-language
    question under-weights the entity token relative to generic words
    (adult, dose, maximum, document, …).
    """

    @property
    def expander_id(self) -> str:
        return "entity_hint"

    @property
    def expansion_type(self) -> str:
        return "entity_hint"

    def expand(self, context: ExpansionContext) -> ExpansionResult:
        original = (context.query_text or "").strip()
        variants: list[str] = []
        if original:
            variants.append(original)

        entities = [e.strip() for e in context.entities if e and e.strip()]
        if entities:
            entity_phrase = " ".join(entities)
            # Prefer entity + remaining content words from the question.
            extras = [
                tok
                for tok in original.replace("?", " ").split()
                if tok.lower() not in {e.lower() for e in entities}
                and len(tok) > 2
            ]
            hint = f"{entity_phrase} {' '.join(extras[:8])}".strip()
            if hint and hint.lower() != original.lower():
                variants.append(hint)
            # Ultra-short entity-only variant for sparse/keyword legs.
            if entity_phrase.lower() not in {v.lower() for v in variants}:
                variants.append(entity_phrase)

        if not variants:
            variants = [original or ""]

        return ExpansionResult(
            variants=tuple(variants[: max(1, context.max_variants)]),
            expansion_type="entity_hint",
            metadata={"entity_count": len(entities)},
        )

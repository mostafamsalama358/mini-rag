"""Final-pass char n-gram Jaccard deduplication."""

from __future__ import annotations

from core.context_builder.config import ContextBuilderConfig
from core.evidence_orchestrator.models import EvidenceItem
from core.evidence_orchestrator.text_similarity import char_ngrams, jaccard_similarity


class FinalPassDeduplicator:
    def deduplicate(
        self,
        items: list[EvidenceItem],
        config: ContextBuilderConfig,
    ) -> tuple[list[EvidenceItem], int]:
        if not config.final_dedup_enabled or len(items) < 2:
            return list(items), 0

        to_remove: set[str] = set()
        comparisons = 0
        max_pairs = config.final_dedup_max_pairs
        threshold = config.final_dedup_similarity_threshold

        ngram_cache = {item.item_id: char_ngrams(item.text) for item in items}

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if comparisons >= max_pairs:
                    break
                comparisons += 1

                item_i = items[i]
                item_j = items[j]
                if item_i.item_id in to_remove or item_j.item_id in to_remove:
                    continue

                similarity = jaccard_similarity(
                    ngram_cache[item_i.item_id],
                    ngram_cache[item_j.item_id],
                )
                if similarity >= threshold:
                    if item_i.relevance_score >= item_j.relevance_score:
                        to_remove.add(item_j.item_id)
                    else:
                        to_remove.add(item_i.item_id)

        return _filter_items(items, to_remove)


def _filter_items(
    items: list[EvidenceItem],
    to_remove: set[str],
) -> tuple[list[EvidenceItem], int]:
    if not to_remove:
        return list(items), 0
    kept = [item for item in items if item.item_id not in to_remove]
    return kept, len(to_remove)

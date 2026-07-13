"""services/rag/enrichment.py — retrieved-document context enrichment.

Split out of `NLPController` (003 refactor Phase 4c). Enriches the reranked
candidate set with continuation chunks (the next chunk after a header) and
structural context (sibling article/chapter chunks). Pure extraction — every
method body is identical to the original controller methods; they now take
their collaborators (ChunkModel, project) explicitly.
"""
from __future__ import annotations

from models.db_schemes import Project, RetrievedDocument
from repositories.chunk_repository import ChunkModel
from core.retrieval import (
    continuation_chunk_key,
    needs_continuation_chunk,
    _source_key,
)
from core.structural.engine import (
    extract_structural_targets,
    is_structural_reference_query,
    starts_different_chapter,
    text_references_chapter,
    article_context_limit,
    collect_article_context_chunks,
)


def append_chunk_if_new(*, extras, existing_keys, chunk, score) -> None:
    sibling_key = _source_key(chunk.chunk_metadata)
    if sibling_key and sibling_key in existing_keys:
        return

    if sibling_key:
        existing_keys.add(sibling_key)

    extras.append(
        RetrievedDocument(
            text=chunk.chunk_text,
            score=score,
            metadata=chunk.chunk_metadata,
        )
    )


async def expand_structural_context(
    *,
    project: Project,
    documents: list[RetrievedDocument],
    chunk_model: ChunkModel,
    query: str,
    existing_keys: set[str],
    structural_patterns=None,
) -> list[RetrievedDocument]:
    targets = extract_structural_targets(query, patterns=structural_patterns)
    if not targets["article_numbers"] and not targets["chapter_labels"]:
        return []

    enriched_extras: list[RetrievedDocument] = []
    seed_documents = sorted(documents, key=lambda item: item.score, reverse=True)[:5]
    asset_ids: set[int] = set()

    for document in seed_documents:
        metadata = document.metadata or {}
        asset_id = metadata.get("asset_id")
        if asset_id is None:
            continue
        try:
            asset_ids.add(int(asset_id))
        except (TypeError, ValueError):
            continue

    for asset_id_int in asset_ids:
        asset_chunks = await chunk_model.get_chunks_by_asset(
            project_id=project.project_id,
            asset_id=asset_id_int,
        )

        for article_number in targets["article_numbers"]:
            context_chunks = collect_article_context_chunks(
                asset_chunks,
                article_number,
                max_chunks=article_context_limit(query),
                patterns=structural_patterns,
            )
            for index, chunk in enumerate(context_chunks):
                append_chunk_if_new(
                    extras=enriched_extras,
                    existing_keys=existing_keys,
                    chunk=chunk,
                    score=0.98 - index * 0.005,
                )

        for document in seed_documents:
            metadata = document.metadata or {}
            if metadata.get("asset_id") != asset_id_int:
                continue

            chunk_order = metadata.get("chunk_order")
            page = metadata.get("page")

            if page is not None:
                try:
                    page_int = int(page)
                except (TypeError, ValueError):
                    page_int = None

                if page_int is not None:
                    for page_chunk in await chunk_model.get_chunks_by_asset_page(
                        project_id=project.project_id,
                        asset_id=asset_id_int,
                        page=page_int,
                    ):
                        append_chunk_if_new(
                            extras=enriched_extras,
                            existing_keys=existing_keys,
                            chunk=page_chunk,
                            score=max(document.score, 0.96),
                        )

            for chapter_label in targets["chapter_labels"]:
                if chunk_order is None:
                    continue
                if not text_references_chapter(document.text, chapter_label, patterns=structural_patterns):
                    continue

                start_order = int(chunk_order)
                for offset in range(0, 12):
                    order = start_order + offset
                    sibling = await chunk_model.get_chunk_by_asset_order(
                        project_id=project.project_id,
                        asset_id=asset_id_int,
                        chunk_order=order,
                    )
                    if sibling is None:
                        break
                    if offset > 0 and starts_different_chapter(
                        sibling.chunk_text,
                        chapter_label,
                        patterns=structural_patterns,
                    ):
                        break
                    append_chunk_if_new(
                        extras=enriched_extras,
                        existing_keys=existing_keys,
                        chunk=sibling,
                        score=max(document.score, 0.95 - offset * 0.01),
                    )

    return enriched_extras


async def enrich_retrieved_documents(
    *,
    project: Project,
    documents: list[RetrievedDocument],
    chunk_model: ChunkModel,
    query: str = "",
    structural_patterns=None,
) -> list[RetrievedDocument]:
    if not documents or chunk_model is None:
        return documents

    existing_keys = {
        key
        for doc in documents
        if (key := _source_key(doc.metadata))
    }
    enriched_extras: list[RetrievedDocument] = []

    for document in documents:
        if not needs_continuation_chunk(document.text):
            continue

        continuation_key = continuation_chunk_key(document.metadata)
        if not continuation_key:
            continue

        asset_id, next_order = continuation_key
        sibling = await chunk_model.get_chunk_by_asset_order(
            project_id=project.project_id,
            asset_id=asset_id,
            chunk_order=next_order,
        )
        if sibling is None:
            continue

        append_chunk_if_new(
            extras=enriched_extras,
            existing_keys=existing_keys,
            chunk=sibling,
            score=max(document.score, 0.95),
        )

    if is_structural_reference_query(query, patterns=structural_patterns):
        enriched_extras.extend(
            await expand_structural_context(
                project=project,
                documents=documents,
                chunk_model=chunk_model,
                query=query,
                existing_keys=existing_keys,
                structural_patterns=structural_patterns,
            )
        )

    if not enriched_extras:
        return documents

    combined = list(documents) + enriched_extras
    return sorted(combined, key=lambda item: item.score, reverse=True)

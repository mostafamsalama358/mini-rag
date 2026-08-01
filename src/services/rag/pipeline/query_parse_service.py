"""Shared query-parse stage for legacy and unified pipeline paths."""

from __future__ import annotations

from typing import Any

from core.query_parser import build_conversation_context, semantic_parse_async
from core.query_parser.grounding import build_catalog_fingerprint_index
from core.query_parser.normalize import normalize_query_text as semantic_normalize_query_text
from core.query_parser.schema import ParseResult
from models.db_schemes import Project
from repositories.chat_message_repository import ChatMessageModel
from repositories.chunk_repository import ChunkModel
from services.FieldRegistry import FieldProfile

_catalog_lexicon_cache: dict[int, tuple[list[str], dict[str, list[str]]]] = {}


class QueryParseService:
    """Extracted parse stage — single path for legacy and unified orchestrators."""

    def __init__(self, *, generation_client: Any, db_client: Any = None) -> None:
        self.generation_client = generation_client
        self.db_client = db_client

    async def _load_catalog_for_parser(
        self,
        project: Project,
        profile: FieldProfile,
    ) -> tuple[list[str], dict[str, list[str]]]:
        project_id = int(project.project_id)
        cached = _catalog_lexicon_cache.get(project_id)
        if cached is not None:
            return cached

        parser_profile = profile.parser_profile
        metadata_keys = list(parser_profile.entity_grounding.metadata_keys or [])
        if not metadata_keys or self.db_client is None:
            return [], {}

        chunk_model = await ChunkModel.create_instance(self.db_client)
        terms = await chunk_model.get_distinct_metadata_tokens(
            project_id,
            metadata_keys=metadata_keys,
        )
        index = build_catalog_fingerprint_index(terms)
        lexicon = (terms, index)
        _catalog_lexicon_cache[project_id] = lexicon
        return lexicon

    async def parse(
        self,
        *,
        project: Project,
        query: str,
        profile: FieldProfile,
        session_id: str | None = None,
    ) -> tuple[ParseResult, list | None]:
        """Return (ParseResult, prior_messages). prior_messages may be None."""
        normalized_query = semantic_normalize_query_text(query, profile.config)
        parser_profile = profile.parser_profile

        prior_messages = None
        if session_id and self.db_client is not None:
            chat_message_model = await ChatMessageModel.create_instance(self.db_client)
            prior_messages = await chat_message_model.get_chat_history(
                session_id=session_id,
                project_id=project.project_id,
            )

        conversation_context = build_conversation_context(
            domain_key=profile.domain_key,
            document_language=parser_profile.document_language,
            chat_messages=prior_messages or [],
            context_turn_window=parser_profile.context_turn_window,
        )

        catalog_terms, fingerprint_index = await self._load_catalog_for_parser(project, profile)
        parse_result = await semantic_parse_async(
            normalized_query,
            generation_client=self.generation_client,
            profile=profile,
            conversation_context=conversation_context,
            catalog_terms=catalog_terms or None,
            catalog_fingerprint_index=fingerprint_index or None,
        )
        return parse_result, prior_messages

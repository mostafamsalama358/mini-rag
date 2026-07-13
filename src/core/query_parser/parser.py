"""LLM semantic parse orchestration with timeout, retry, and degradation."""
from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback

from pydantic import ValidationError

from fields.schemas import FieldRegistryProfile, ParserProfile
from services.FieldRegistry import FieldProfile
from stores.llm.errors import VertexGenerationError

from .errors import SemanticParseJsonError
from .grounding import ground_entity, infer_entity_from_query
from .json_extract import extract_json_object
from .normalize import normalize_query_text
from .schema import ConversationContext, ParseResult, QueryPlan
from .validator import validate_query_plan

logger = logging.getLogger("uvicorn.error")

PARSER_LLM_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "canonical_query": {"type": "string"},
        "query_plan": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "nullable": True},
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "field": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": [
                        "lookup",
                        "list",
                        "compare",
                        "explain",
                        "count",
                        "unsupported",
                    ],
                },
                "scope": {
                    "type": "string",
                    "enum": ["all", "single", "subset"],
                },
                "language": {"type": "string"},
                "filters": {"type": "object"},
                "confidence": {"type": "number", "nullable": True},
                "needs_clarification": {"type": "boolean"},
                "clarification_prompt": {"type": "string", "nullable": True},
            },
            "required": ["field", "operation", "scope", "language"],
        },
    },
    "required": ["canonical_query", "query_plan"],
}


def _heuristic_plan_from_query(
    query: str,
    *,
    language: str,
    catalog_terms: list[str] | None,
    fingerprint_index: dict[str, list[str]] | None,
    min_score: float,
    entity_aliases: dict[str, str] | None = None,
) -> tuple[QueryPlan, str] | None:
    """Catalog-only fallback when the LLM parse fails."""
    entity, _score = infer_entity_from_query(
        query,
        catalog_terms,
        fingerprint_index,
        min_score=min_score,
        entity_aliases=entity_aliases,
    )
    if not entity:
        return None

    q = (query or "").lower()
    field = "unknown"
    operation = "lookup"
    scope = "single"
    if any(k in q for k in ("strength", "strengths", "تركيز", "تركيزات", "mg", "mcg")):
        field = "strengths"
        operation = "list"
        scope = "all" if any(k in q for k in ("all", "every", "كل", "جميع")) else "single"
    elif any(k in q for k in ("dosage", "dose", "جرعة", "جرعات", "كم")):
        field = "dosage"
    elif any(k in q for k in ("interaction", "interactions", "تعارض", "متعارض")):
        field = "interactions"
        operation = "list"

    canonical = query
    if field == "strengths" and scope == "all":
        canonical = f"all {entity} strengths"
    elif field == "dosage":
        canonical = f"{entity} dosage"
    elif field == "interactions":
        canonical = f"{entity} interactions"

    plan = QueryPlan(
        entity=entity,
        field=field,
        operation=operation,
        scope=scope,
        language=language[:2] if language else "en",
        needs_clarification=False,
    )
    return plan, canonical


def _fallback_plan(*, language: str, needs_clarification: bool = True) -> QueryPlan:
    return QueryPlan(
        entity=None,
        field="unknown",
        operation="unsupported",
        scope="single",
        language=language[:2] if language else "en",
        needs_clarification=needs_clarification,
        clarification_prompt=(
            "I could not understand your question. Please rephrase or name a specific item."
            if needs_clarification
            else None
        ),
    )


def _field_vocabulary(registry: FieldRegistryProfile, profile: ParserProfile) -> list[str]:
    if profile.allowed_fields:
        return list(profile.allowed_fields)
    return [c.concept for c in registry.concepts]


def _build_parser_prompt(
    *,
    profile: ParserProfile,
    registry: FieldRegistryProfile,
    conversation_context: ConversationContext,
    query: str,
) -> str:
    fields = _field_vocabulary(registry, profile)
    field_lines = []
    for concept in registry.concepts:
        if concept.concept not in fields:
            continue
        synonyms = ", ".join(concept.synonyms[:8])
        field_lines.append(f"- {concept.concept}: {synonyms}")

    turns_text = ""
    for turn in conversation_context.recent_turns:
        prior_plan = turn.query_plan
        entity_note = prior_plan.entity if prior_plan else "none"
        turns_text += (
            f"User: {turn.user_text}\n"
            f"Canonical: {turn.canonical_query or 'n/a'}\n"
            f"Entity: {entity_note}\n\n"
        )

    template = profile.prompt or (
        "Parse the pharmacy question into JSON with keys canonical_query and query_plan."
    )
    return (
        f"{template}\n\n"
        f"Allowed fields:\n" + "\n".join(field_lines) + "\n\n"
        f"Document language: {profile.document_language}\n"
        f"Current entity from session: {conversation_context.current_entity or 'none'}\n"
        f"Recent turns:\n{turns_text or '(none)'}\n"
        f"User question: {query}\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"canonical_query":"...", "query_plan":{"entity":null,"field":"...","operation":"lookup|list|compare|explain|count|unsupported","scope":"all|single|subset","language":"en","needs_clarification":false}}'
    )


def _parse_llm_json(raw: str) -> tuple[str, QueryPlan]:
    logger.debug("LLM raw response: %r", raw)
    text = (raw or "").strip()
    logger.debug("LLM stripped response: %r", text)
    if not text:
        raise SemanticParseJsonError(
            "empty_llm_output",
            "empty_llm_output: LLM returned no text",
            raw=raw,
        )

    payload_text = extract_json_object(text)
    logger.debug("LLM payload: %r", payload_text)
    logger.debug("LLM payload length: %r", len(payload_text) if payload_text else 0)

    if not payload_text:
        raise SemanticParseJsonError(
            "no_json_found",
            "no_json_found: no JSON object found in LLM output",
            raw=raw,
            payload_text=None,
        )

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise SemanticParseJsonError(
            "invalid_json",
            f"invalid_json: {exc.msg} at char {exc.pos}",
            raw=raw,
            payload_text=payload_text,
            cause=exc,
        ) from exc

    if not isinstance(payload, dict):
        raise SemanticParseJsonError(
            "invalid_json_root",
            f"invalid_json_root: expected object, got {type(payload).__name__}",
            raw=raw,
            payload_text=payload_text,
        )

    canonical = str(payload.get("canonical_query") or "").strip()
    plan_raw = payload.get("query_plan")
    if not isinstance(plan_raw, dict):
        raise SemanticParseJsonError(
            "missing_query_plan",
            "missing_query_plan: query_plan must be a JSON object",
            raw=raw,
            payload_text=payload_text,
        )

    try:
        plan = QueryPlan.model_validate(plan_raw)
    except ValidationError as exc:
        raise SemanticParseJsonError(
            "schema_validation_failed",
            f"schema_validation_failed: {exc.error_count()} validation error(s)",
            raw=raw,
            payload_text=payload_text,
            cause=exc,
        ) from exc

    if not canonical:
        canonical = query_fallback_text(plan)
    return canonical, plan


def query_fallback_text(plan: QueryPlan) -> str:
    entity = plan.entity or "the item"
    return f"{plan.operation} {plan.field} for {entity}."


async def semantic_parse_async(
    query: str,
    *,
    generation_client,
    profile: FieldProfile,
    conversation_context: ConversationContext,
    catalog_terms: list[str] | None = None,
    catalog_fingerprint_index: dict[str, list[str]] | None = None,
) -> ParseResult:
    """Parse user question into canonical query + QueryPlan."""
    parser_profile: ParserProfile = getattr(profile, "parser_profile", ParserProfile())
    registry = profile.field_registry
    start = time.perf_counter()
    original = normalize_query_text(query, profile.config)

    if not original.strip():
        latency_ms = (time.perf_counter() - start) * 1000.0
        plan = _fallback_plan(language=parser_profile.document_language)
        return ParseResult(
            original_query=query or "",
            canonical_query=query or "",
            query_plan=plan,
            used_llm=False,
            latency_ms=latency_ms,
            error="empty_query",
        )

    generate_async = getattr(generation_client, "generate_text_async", None)
    generate_sync = getattr(generation_client, "generate_text", None)
    prompt = _build_parser_prompt(
        profile=parser_profile,
        registry=registry,
        conversation_context=conversation_context,
        query=original,
    )
    timeout = parser_profile.timeout_seconds
    max_tokens = parser_profile.max_output_tokens
    temperature = parser_profile.temperature
    grounding_cfg = parser_profile.entity_grounding

    async def _call() -> str | None:
        llm_kwargs = {
            "prompt": prompt,
            "chat_history": [],
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_schema": PARSER_LLM_RESPONSE_SCHEMA,
        }
        if generate_async is not None:
            return await generate_async(**llm_kwargs)
        if generate_sync is not None:
            return await asyncio.to_thread(generate_sync, **llm_kwargs)
        return None

    used_llm = False
    error: str | None = None
    canonical_query = original
    plan = _fallback_plan(language=parser_profile.document_language, needs_clarification=False)

    for attempt in range(2):
        raw: str | None = None
        payload_text: str | None = None
        failure_category: str | None = None
        try:
            raw = await asyncio.wait_for(_call(), timeout=timeout)
            canonical_query, plan = _parse_llm_json(raw or "")
            used_llm = True
            error = None
            break
        except asyncio.TimeoutError:
            failure_category = "timeout"
            error = "timeout"
            logger.warning(
                "Semantic parse timed out after %.1fs attempt=%d category=%r raw=%r payload=%r",
                timeout,
                attempt + 1,
                failure_category,
                raw,
                payload_text,
                exc_info=True,
            )
        except SemanticParseJsonError as exc:
            failure_category = exc.category
            raw = exc.raw if exc.raw is not None else raw
            payload_text = exc.payload_text
            error = str(exc)
            logger.warning(
                "Semantic parse failed attempt=%d category=%r raw=%r payload=%r payload_len=%r error=%r",
                attempt + 1,
                failure_category,
                raw,
                payload_text,
                len(payload_text) if payload_text else 0,
                error,
                exc_info=True,
            )
        except VertexGenerationError as exc:
            failure_category = exc.category
            error = str(exc)
            logger.warning(
                "Semantic parse vertex failure attempt=%d category=%r diagnostics=%r error=%r",
                attempt + 1,
                failure_category,
                exc.diagnostics,
                error,
                exc_info=True,
            )
        except Exception as exc:
            failure_category = type(exc).__name__
            error = str(exc)
            logger.warning(
                "Semantic parse unexpected failure attempt=%d category=%r raw=%r payload=%r error=%r traceback=%r",
                attempt + 1,
                failure_category,
                raw,
                payload_text,
                error,
                traceback.format_exc(),
                exc_info=True,
            )

    if error and not used_llm:
        heuristic = _heuristic_plan_from_query(
            original,
            language=parser_profile.document_language,
            catalog_terms=catalog_terms,
            fingerprint_index=catalog_fingerprint_index,
            min_score=0.55,
            entity_aliases=grounding_cfg.entity_aliases or None,
        )
        if heuristic is not None:
            plan, canonical_query = heuristic
            error = "heuristic_fallback"
        else:
            plan = _fallback_plan(language=parser_profile.document_language)

    if (
        not plan.entity
        and conversation_context.current_entity
        and not plan.needs_clarification
    ):
        plan = plan.model_copy(update={"entity": conversation_context.current_entity})

    plan = validate_query_plan(plan, registry, parser_profile=parser_profile)

    plan, grounding_score = ground_entity(
        plan,
        catalog_terms,
        catalog_fingerprint_index,
        min_score=grounding_cfg.min_score,
        enabled=grounding_cfg.enabled,
        entity_aliases=grounding_cfg.entity_aliases or None,
    )

    if not plan.needs_clarification and not canonical_query.strip():
        canonical_query = query_fallback_text(plan)

    latency_ms = (time.perf_counter() - start) * 1000.0
    outcome = "clarify" if plan.needs_clarification else ("fallback" if error else "ok")
    logger.info(
        "query_parse_complete domain=%s outcome=%s latency_ms=%.1f entity=%s field=%s",
        profile.domain_key,
        outcome,
        latency_ms,
        plan.entity,
        plan.field,
    )

    return ParseResult(
        original_query=original,
        canonical_query=canonical_query,
        query_plan=plan,
        used_llm=used_llm,
        latency_ms=latency_ms,
        grounding_score=grounding_score,
        error=error,
    )

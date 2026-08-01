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
from .grounding import ground_entity, infer_entity_from_query, _LATIN_TOKEN_RE
from .json_extract import extract_json_object
from .normalize import normalize_query_text
from .need_frame import NeedFrame
from .schema import ConversationContext, ParseResult, QueryPlan
from .validator import validate_query_plan
from utils.detect_language import detect_query_language

_PRODUCT_LINE_SECONDS = frozenset(
    {
        "ADVANCE",
        "EXTRA",
        "JOINT",
        "MIGRAINE",
        "SINUS",
        "RELIEF",
        "COLD",
        "FLU",
        "DAY",
        "NIGHT",
        "ACUTE",
        "HEAD",
        "VAPOUR",
        "VAPOR",
        "PE",
        "FORTE",
        "PLUS",
        "ALL",
        "ONE",
    }
)

# English filler / narrative words — never treat as drug entities in heuristic
# recovery (e.g. "Patient already took…" must not become entity=already).
_LATIN_ENTITY_STOPWORDS = frozenset(
    {
        "THE", "AND", "FOR", "WITH", "FROM", "WHAT", "IS", "ARE", "CAN",
        "SAFE", "SAME", "DOSE", "ADULT", "PATIENT", "TAKE", "TAKING", "TOOK",
        "TOGETHER", "BETWEEN", "ABOUT", "HAVE", "HAS", "DOES", "VS",
        "MG", "ML", "GRAM", "GRAMS",
        "ALREADY", "TODAY", "TONIGHT", "YESTERDAY", "TOMORROW",
        "VARIOUS", "STILL", "THEY", "THEM", "THEIR", "THIS", "THAT",
        "THESE", "THOSE", "WHEN", "WHERE", "WHICH", "WHO", "WHOM", "WHY",
        "WILL", "WOULD", "COULD", "SHOULD", "SHALL", "MIGHT", "MUST",
        "ALSO", "ONLY", "MORE", "MOST", "OTHER", "SOME", "SUCH", "THAN",
        "THEN", "THERE", "INTO", "OVER", "AFTER", "BEFORE", "DURING",
        "THROUGH", "UNDER", "AGAIN", "ONCE", "HERE", "JUST", "VERY",
        "MUCH", "MANY", "EACH", "BOTH", "FEW", "OWN", "TOO", "NOW",
        "PRODUCT", "PRODUCTS", "COLD", "CRAMP", "ABDOMINAL", "NIGHT",
        "BEEN", "BEING", "WERE", "WAS", "HAD", "DID", "DONE", "DOING",
        "NOT", "YES", "PLEASE", "HELP", "ASK", "TELL", "GIVE", "GIVEN",
        "USED", "USING", "USE", "LIKE", "WANT", "NEED", "NEEDS",
    }
)

logger = logging.getLogger("uvicorn.error")


def _recover_latin_brand_entity(query: str) -> str | None:
    """Best-effort brand recovery when catalog lexicon is empty.

    Prefers capitalized / product-line tokens (``Buscopan Plus``,
    ``Panadol Advance``) and skips English narrative filler
    (``already``, ``patient``, ``today``, …).
    """
    matches = list(_LATIN_TOKEN_RE.finditer(query or ""))
    if not matches:
        return None

    candidates: list[tuple[int, int, str]] = []
    tokens = [m.group(0) for m in matches]
    for idx, tok in enumerate(tokens):
        upper = tok.upper()
        if upper in _LATIN_ENTITY_STOPWORDS or len(tok) < 4:
            continue
        # Brand-like if original token starts with a capital (Buscopan / BUSCOPAN).
        brand_like = tok[0].isupper()
        parts = [tok]
        priority = 2 if brand_like else 0
        if idx + 1 < len(tokens):
            nxt = tokens[idx + 1]
            if nxt.upper() in _PRODUCT_LINE_SECONDS:
                parts = [tok, nxt]
                priority = max(priority, 3 if brand_like else 1)
                for j in range(idx + 2, min(idx + 4, len(tokens))):
                    nxt2 = tokens[j]
                    if nxt2.upper() in _PRODUCT_LINE_SECONDS:
                        parts.append(nxt2)
                    else:
                        break
        if priority == 0 and not brand_like:
            # Keep lowercase INN/brand fallbacks (paracetamol) at low priority
            # so capitalized Buscopan wins when both appear.
            priority = 0
        candidates.append((priority, idx, " ".join(parts)))

    if not candidates:
        return None
    # Highest priority, then latest mention (often the drug being asked about).
    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[-1][2]


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


def _population_from_query(query: str) -> str | None:
    q = (query or "").casefold()
    if any(k in q for k in ("pregnan", "حمل", "حامل")):
        return "pregnancy"
    if any(k in q for k in ("breast", "lactat", "رضاع")):
        return "breastfeeding"
    return None


def _try_recommend_plan(query: str, *, language: str) -> tuple[QueryPlan, str] | None:
    """Need-based recommend heuristic when no brand entity is present (Feature 020)."""
    q = (query or "").strip()
    if not q:
        return None
    ql = q.casefold()
    if any(k in ql for k in ("what is", "ما هو", "interactions", "تعارض", "جرعة", "dosage", "strength")):
        # Prefer entity/field lookup postures for these cues
        if not any(c in ql or c in q for c in ("دواء ل", "medicine for", "something for", "drug for")):
            return None

    try:
        from services.rag.domain_helpers import load_domain_helper

        map_need = load_domain_helper("pharmacy", "taxonomy_mapper", "map_need")
        if map_need is None:
            return None
    except Exception:
        return None

    match = map_need(q)
    recommend_cues = (
        "دواء ل",
        "دوا ل",
        "علاج ل",
        "medicine for",
        "something for",
        "drug for",
        "recommend",
        "suggestion for",
        "what can i take for",
        "ايه دوا",
        "أي دواء",
    )
    has_cue = any(c in ql or c in q for c in recommend_cues)
    if not match.node_ids and not has_cue and match.confidence < 0.35:
        return None

    population = _population_from_query(q)
    need_frame = NeedFrame(
        normalized_need=match.node_ids[0] if match.node_ids else None,
        population=population,
        language=language[:2] if language else "en",
        confidence=match.confidence,
        raw_need_span=q,
        indication_tags=list(match.indication_tags),
        taxonomy_node_ids=list(match.node_ids),
        ambiguity_group=match.ambiguity_group,
        multiple_symptoms=list(match.node_ids) if len(match.node_ids) > 1 else [],
    )
    needs_clarification = bool(match.ambiguity_group) or match.confidence < 0.55
    clarification = match.clarification_prompt
    if needs_clarification and not clarification:
        clarification = (
            "هل يمكنك توضيح العرض بشكل أدق؟"
            if (language or "").startswith("ar")
            else "Could you clarify the symptom more precisely?"
        )
    plan = QueryPlan(
        entity=None,
        field="indications",
        operation="recommend",
        scope="all",
        language=language[:2] if language else "en",
        confidence=match.confidence,
        needs_clarification=needs_clarification,
        clarification_prompt=clarification if needs_clarification else None,
        recommend_mode=True,
        need_frame=need_frame,
        filters={"indication_tags": list(match.indication_tags)},
    )
    canonical = f"recommend therapy for {need_frame.normalized_need or 'need'}"
    return plan, canonical


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
    # When the project catalog lexicon is empty/unavailable, still recover an
    # explicit Latin brand / product-line from the user text
    # (e.g. "Panadol Advance", "Buscopan Plus") — never English filler words.
    if not entity:
        entity = _recover_latin_brand_entity(query or "")
    if not entity:
        recommend = _try_recommend_plan(query, language=language)
        if recommend is not None:
            return recommend
        return None

    q = (query or "").lower()
    field = "unknown"
    operation = "lookup"
    scope = "single"
    if any(k in q for k in ("strength", "strengths", "تركيز", "تركيزات", "mg", "mcg")):
        field = "strengths"
        operation = "list"
        scope = "all" if any(k in q for k in ("all", "every", "كل", "جميع")) else "single"
    elif any(
        k in q
        for k in (
            "interaction",
            "interactions",
            "تعارض",
            "متعارض",
            "خطر",
            "يخوف",
            "together",
            "combine",
            "combined",
            "مع بعض",
            "مع بعضه",
            "stack",
            "still take",
            "already took",
            "why not",
            "why/why",
        )
    ):
        field = "interactions"
        operation = "list"
    elif any(k in q for k in ("dosage", "dose", "جرعة", "جرعات", "كم")):
        field = "dosage"
    elif any(k in q for k in ("pregnan", "حمل", "حامل")):
        field = "pregnancy"
    elif any(k in q for k in ("breast", "رضاع", "رضاعة")):
        field = "breastfeeding"

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
    lang = (language or "en")[:2].lower()
    if needs_clarification:
        clarification = (
            "لم أفهم سؤالك. أعد الصياغة أو اذكر اسم دواء/منتج محدد."
            if lang == "ar"
            else "I could not understand your question. Please rephrase or name a specific item."
        )
    else:
        clarification = None
    return QueryPlan(
        entity=None,
        field="unknown",
        operation="unsupported",
        scope="single",
        language=lang or "en",
        needs_clarification=needs_clarification,
        clarification_prompt=clarification,
    )


def _force_query_language(plan: QueryPlan, query: str, *, fallback: str = "en") -> QueryPlan:
    """Prefer user-script language over document_language / LLM rewrite to English."""
    detected = detect_query_language(query, default=(fallback or "en")[:2])
    if plan.language == detected:
        return plan
    return plan.model_copy(update={"language": detected})


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
        "Respond with ONLY valid JSON.\n"
        "Set query_plan.language to 'ar' when the user question contains Arabic script, "
        "otherwise 'en'. Keep brand names Latin in canonical_query if helpful for retrieval, "
        "but never set language=en for an Arabic user question.\n"
        '{"canonical_query":"...", "query_plan":{"entity":null,"entities":[],"field":"...","operation":"lookup|list|compare|explain|count|unsupported","scope":"all|single|subset","language":"ar|en","needs_clarification":false}}'
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
        plan = _fallback_plan(
            language=detect_query_language(query or "", default="en")
        )
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
    client_name = type(generation_client).__name__ if generation_client is not None else "none"
    generation_model = getattr(generation_client, "generation_model_id", None) or getattr(
        generation_client, "model_id", None
    )

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
    query_lang = detect_query_language(
        original, default=(parser_profile.document_language or "en")[:2]
    )
    plan = _fallback_plan(language=query_lang, needs_clarification=False)

    for attempt in range(2):
        raw: str | None = None
        payload_text: str | None = None
        failure_category: str | None = None
        attempt_started = time.perf_counter()
        logger.info(
            "semantic_parse_llm_start attempt=%d/%d timeout_s=%.1f client=%s model=%s "
            "prompt_chars=%d max_output_tokens=%d temperature=%s query_preview=%r "
            "catalog_terms=%d",
            attempt + 1,
            2,
            timeout,
            client_name,
            generation_model,
            len(prompt or ""),
            max_tokens,
            temperature,
            (original[:160] + ("…" if len(original) > 160 else "")),
            len(catalog_terms or []),
        )
        try:
            raw = await asyncio.wait_for(_call(), timeout=timeout)
            elapsed_ms = (time.perf_counter() - attempt_started) * 1000.0
            logger.info(
                "semantic_parse_llm_done attempt=%d elapsed_ms=%.1f raw_chars=%d raw_preview=%r",
                attempt + 1,
                elapsed_ms,
                len(raw or ""),
                ((raw or "")[:200] + ("…" if len(raw or "") > 200 else "")),
            )
            canonical_query, plan = _parse_llm_json(raw or "")
            used_llm = True
            error = None
            break
        except asyncio.TimeoutError:
            failure_category = "timeout"
            error = "timeout"
            elapsed_ms = (time.perf_counter() - attempt_started) * 1000.0
            # wait_for cancels the in-flight Vertex thread → CancelledError in the
            # traceback; that is expected, not a separate bug.
            logger.warning(
                "semantic_parse_llm_timeout attempt=%d elapsed_ms=%.1f timeout_s=%.1f "
                "client=%s model=%s prompt_chars=%d query_preview=%r "
                "note='Vertex call cancelled by wait_for; no raw payload yet'",
                attempt + 1,
                elapsed_ms,
                timeout,
                client_name,
                generation_model,
                len(prompt or ""),
                (original[:160] + ("…" if len(original) > 160 else "")),
            )
            # A second attempt after a hard timeout usually burns another full
            # budget under the same Vertex latency/quota pressure.
            break
        except SemanticParseJsonError as exc:
            failure_category = exc.category
            raw = exc.raw if exc.raw is not None else raw
            payload_text = exc.payload_text
            error = str(exc)
            elapsed_ms = (time.perf_counter() - attempt_started) * 1000.0
            logger.warning(
                "semantic_parse_llm_failed attempt=%d elapsed_ms=%.1f category=%r "
                "raw_chars=%d raw_preview=%r payload_len=%r error=%r",
                attempt + 1,
                elapsed_ms,
                failure_category,
                len(raw or ""),
                ((raw or "")[:240] + ("…" if len(raw or "") > 240 else "")),
                len(payload_text) if payload_text else 0,
                error,
            )
        except VertexGenerationError as exc:
            failure_category = exc.category
            error = str(exc)
            elapsed_ms = (time.perf_counter() - attempt_started) * 1000.0
            logger.warning(
                "semantic_parse_vertex_failure attempt=%d elapsed_ms=%.1f category=%r "
                "diagnostics=%r error=%r",
                attempt + 1,
                elapsed_ms,
                failure_category,
                exc.diagnostics,
                error,
            )
            # Quota/exhaustion will not recover within the same request — skip
            # the second LLM attempt and fall through to catalog heuristic.
            if failure_category in {"vertex_quota", "vertex_blocked_response"}:
                break
        except Exception as exc:
            failure_category = type(exc).__name__
            error = str(exc)
            elapsed_ms = (time.perf_counter() - attempt_started) * 1000.0
            logger.warning(
                "semantic_parse_unexpected_failure attempt=%d elapsed_ms=%.1f category=%r "
                "raw_preview=%r error=%r traceback=%r",
                attempt + 1,
                elapsed_ms,
                failure_category,
                ((raw or "")[:200] if raw else None),
                error,
                traceback.format_exc(),
            )

    if error and not used_llm:
        heuristic = _heuristic_plan_from_query(
            original,
            language=query_lang,
            catalog_terms=catalog_terms,
            fingerprint_index=catalog_fingerprint_index,
            min_score=0.55,
            entity_aliases=grounding_cfg.entity_aliases or None,
        )
        if heuristic is not None:
            plan, canonical_query = heuristic
            error = "heuristic_fallback"
        else:
            plan = _fallback_plan(language=query_lang)

    if (
        not plan.entity
        and conversation_context.current_entity
        and not plan.needs_clarification
    ):
        plan = plan.model_copy(update={"entity": conversation_context.current_entity})

    plan = validate_query_plan(plan, registry, parser_profile=parser_profile)
    plan = _force_query_language(plan, original, fallback=query_lang)

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

"""Answer Generation async pipeline orchestration."""

from __future__ import annotations

import logging
import re
import time

from core.answer_generation.citation.item_id_formatter import _ITEM_ID_PATTERN
from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.errors import SchemaVersionError
from core.answer_generation.interfaces import (
    ICitationFormatter,
    IGroundingChecker,
    IOutputParser,
    IPromptComposer,
)
from core.answer_generation.models import AnswerResult, ComposedPrompt, GroundingFlag, SCHEMA_VERSION
from core.context_builder.models import Context
from stores.llm.LLMInterface import LLMInterface
from utils.metrics import (
    ANSWER_GENERATION_CITATION_RESOLUTION_TOTAL,
    ANSWER_GENERATION_DURATION_SECONDS,
    ANSWER_GENERATION_GROUNDING_FLAG_TOTAL,
    ANSWER_GENERATION_NO_ANSWER_TOTAL,
)

logger = logging.getLogger(__name__)


def _validate_context_version(context: Context, config: AnswerGenerationConfig) -> None:
    expected_major = config.context_schema_version.split(".", maxsplit=1)[0]
    actual_major = context.schema_version.split(".", maxsplit=1)[0]
    if expected_major != actual_major:
        raise SchemaVersionError(
            f"Context schema major version {actual_major!r} "
            f"does not match expected {expected_major!r}"
        )


def _build_conflict_disclosure(context: Context, config: AnswerGenerationConfig) -> str:
    lines = [config.conflict_disclosure_header.rstrip()]
    for group in context.conflicts:
        item_refs = ", ".join(group.item_ids)
        resolution = (
            f" (resolution: {group.resolution})" if group.resolution else ""
        )
        lines.append(
            f"- {group.entity_tag} / {group.attribute}: conflicting sources "
            f"[{item_refs}]{resolution}"
        )
    lines.append(
        "When answering, explicitly disclose that sources differ on the points above."
    )
    return "\n".join(lines)


def _inject_conflict_disclosure(
    prompt: ComposedPrompt,
    context: Context,
    config: AnswerGenerationConfig,
) -> ComposedPrompt:
    if not context.conflicts:
        return prompt

    disclosure = _build_conflict_disclosure(context, config)
    return prompt.model_copy(
        update={
            "system_message": f"{prompt.system_message.rstrip()}\n\n{disclosure}",
            "has_conflict_disclosure": True,
        }
    )


def _answer_contains_disclosure(answer_text: str, config: AnswerGenerationConfig) -> bool:
    lowered = answer_text.lower()
    header_fragment = config.conflict_disclosure_header.lstrip("#").strip().lower()
    if header_fragment and header_fragment in lowered:
        return True
    for keyword in ("conflict", "sources differ", "conflicting information"):
        if keyword in lowered:
            return True
    return False


def _unresolved_citation_flags(
    answer_text: str,
    citation_map: dict[str, object],
    resolved_ids: set[str],
) -> list[GroundingFlag]:
    flags: list[GroundingFlag] = []
    for match in _ITEM_ID_PATTERN.finditer(answer_text):
        item_id = match.group(1)
        if item_id in citation_map or item_id in resolved_ids:
            continue
        flags.append(
            GroundingFlag(
                entity=item_id,
                claim=match.group(0),
                reason="unresolved_citation",
            )
        )
    return flags


def _provider_name(llm: LLMInterface) -> str:
    return llm.__class__.__name__


class AnswerGenerationPipeline:
    def __init__(
        self,
        *,
        composer: IPromptComposer,
        parser: IOutputParser,
        citation_formatter: ICitationFormatter,
        grounding_checker: IGroundingChecker,
        llm: LLMInterface,
    ) -> None:
        self._composer = composer
        self._parser = parser
        self._citation_formatter = citation_formatter
        self._grounding_checker = grounding_checker
        self._llm = llm

    async def run(
        self,
        *,
        context: Context,
        question: str,
        config: AnswerGenerationConfig,
    ) -> AnswerResult:
        start = time.perf_counter()
        provider = _provider_name(self._llm)

        logger.info(
            "answer_generation_start plan_id=%s context_id=%s provider=%s "
            "blocks=%d token_count=%d",
            context.plan_id,
            context.context_id,
            provider,
            len(context.ordered_blocks),
            context.token_count,
        )

        _validate_context_version(context, config)

        if not context.ordered_blocks:
            ANSWER_GENERATION_NO_ANSWER_TOTAL.inc()
            elapsed = time.perf_counter() - start
            ANSWER_GENERATION_DURATION_SECONDS.observe(elapsed)
            logger.info(
                "answer_generation_end plan_id=%s context_id=%s provider=%s "
                "no_answer=true grounding_flags=0 elapsed_ms=%.2f",
                context.plan_id,
                context.context_id,
                provider,
                elapsed * 1000.0,
            )
            return AnswerResult(
                answer=config.no_answer_message,
                citations=[],
                confidence_note=None,
                conflicts_disclosed=False,
                no_answer=True,
                grounding_flags=[],
                plan_id=context.plan_id,
                context_id=context.context_id,
                schema_version=SCHEMA_VERSION,
            )

        composed = self._composer.compose(context, question, config)
        composed = _inject_conflict_disclosure(composed, context, config)

        chat_history = [
            self._llm.construct_prompt(
                prompt=composed.system_message,
                role=self._llm.enums.SYSTEM.value,
            )
        ]

        raw = await self._llm.generate_text_async(
            prompt=composed.user_message,
            chat_history=chat_history,
            max_output_tokens=config.max_output_tokens,
            temperature=config.temperature,
            response_mime_type="application/json",
        )

        answer_text, confidence_note = self._parser.parse(raw, config)
        llm_no_answer = not answer_text

        if llm_no_answer:
            ANSWER_GENERATION_NO_ANSWER_TOTAL.inc()
            elapsed = time.perf_counter() - start
            ANSWER_GENERATION_DURATION_SECONDS.observe(elapsed)
            logger.info(
                "answer_generation_end plan_id=%s context_id=%s provider=%s "
                "no_answer=true grounding_flags=0 elapsed_ms=%.2f",
                context.plan_id,
                context.context_id,
                provider,
                elapsed * 1000.0,
            )
            return AnswerResult(
                answer=config.no_answer_message,
                citations=[],
                confidence_note=confidence_note,
                conflicts_disclosed=False,
                no_answer=True,
                grounding_flags=[],
                plan_id=context.plan_id,
                context_id=context.context_id,
                schema_version=SCHEMA_VERSION,
            )

        citations = self._citation_formatter.format(answer_text, context.citation_map)
        ANSWER_GENERATION_CITATION_RESOLUTION_TOTAL.inc(len(citations))

        resolved_ids = {citation.citation_id for citation in citations}
        grounding_flags: list[GroundingFlag] = _unresolved_citation_flags(
            answer_text,
            context.citation_map,
            resolved_ids,
        )

        if config.grounding_check_enabled:
            grounding_flags.extend(
                self._grounding_checker.check(answer_text, context)
            )

        if grounding_flags:
            ANSWER_GENERATION_GROUNDING_FLAG_TOTAL.inc(len(grounding_flags))

        conflicts_disclosed = composed.has_conflict_disclosure and _answer_contains_disclosure(
            answer_text,
            config,
        )

        elapsed = time.perf_counter() - start
        ANSWER_GENERATION_DURATION_SECONDS.observe(elapsed)

        logger.info(
            "answer_generation_end plan_id=%s context_id=%s provider=%s "
            "no_answer=false grounding_flags=%d citations=%d elapsed_ms=%.2f",
            context.plan_id,
            context.context_id,
            provider,
            len(grounding_flags),
            len(citations),
            elapsed * 1000.0,
        )

        return AnswerResult(
            answer=answer_text,
            citations=citations,
            confidence_note=confidence_note,
            conflicts_disclosed=conflicts_disclosed,
            no_answer=False,
            grounding_flags=grounding_flags,
            plan_id=context.plan_id,
            context_id=context.context_id,
            schema_version=SCHEMA_VERSION,
        )

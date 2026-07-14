"""Registry wiring concrete Answer Generation stage implementations."""

from __future__ import annotations

from core.answer_generation.composition.default_composer import DefaultPromptComposer
from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.citation.item_id_formatter import ItemIdCitationFormatter
from core.answer_generation.grounding.entity_tag_checker import EntityTagGroundingChecker
from core.answer_generation.parsing.json_output_parser import JsonOutputParser
from core.answer_generation.pipeline import AnswerGenerationPipeline
from stores.llm.LLMInterface import LLMInterface


class AnswerGenerationRegistry:
    @staticmethod
    def build(
        config: AnswerGenerationConfig,
        llm: LLMInterface,
    ) -> AnswerGenerationPipeline:
        _ = config
        grounding_checker = EntityTagGroundingChecker()

        return AnswerGenerationPipeline(
            composer=DefaultPromptComposer(),
            parser=JsonOutputParser(),
            citation_formatter=ItemIdCitationFormatter(),
            grounding_checker=grounding_checker,
            llm=llm,
        )

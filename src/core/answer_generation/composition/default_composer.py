"""Default prompt composer — embeds context blocks with citation markers."""

from __future__ import annotations

from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.interfaces import IPromptComposer
from core.answer_generation.models import ComposedPrompt
from core.context_builder.models import Context


class DefaultPromptComposer(IPromptComposer):
    def compose(
        self,
        context: Context,
        question: str,
        config: AnswerGenerationConfig,
    ) -> ComposedPrompt:
        system_parts = [config.system_prompt_template.rstrip()]

        modules = sorted(config.capability_modules, key=lambda module: module.priority)
        module_names: list[str] = []
        for module in modules:
            module_names.append(module.name)
            system_parts.append(f"\n## Domain Module: {module.name}\n{module.instructions.rstrip()}")

        block_lines: list[str] = []
        for index, block in enumerate(context.ordered_blocks, start=1):
            header = f"[{block.item_id}]"
            if block.section_path:
                header = f"{header} ({block.section_path})"
            block_lines.append(f"{index}. {header}\n{block.text}")

        user_parts = ["## Context", *block_lines, "", f"## Question\n{question.strip()}"]

        return ComposedPrompt(
            system_message="\n".join(system_parts),
            user_message="\n".join(user_parts),
            has_conflict_disclosure=False,
            module_names=module_names,
        )

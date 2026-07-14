"""Shared fixtures for Answer Generation unit tests."""

from __future__ import annotations

import json

import pytest

from core.answer_generation.config import AnswerGenerationConfig
from core.context_builder.models import (
    ConflictGroup,
    Context,
    ContextBlock,
    ContextMetadata,
)
from core.evidence_orchestrator.models import Citation
from stores.llm.LLMInterface import LLMInterface


def _citation(**kwargs) -> Citation:
    defaults = {
        "document_id": "doc_001",
        "chunk_id": "chunk_01",
        "retrieval_score": 0.95,
        "score_source": "hybrid_rrf",
    }
    defaults.update(kwargs)
    return Citation(**defaults)


def make_block(
    *,
    item_id: str,
    text: str,
    document_id: str = "doc_001",
    section_path: str | None = None,
    token_count: int | None = None,
) -> ContextBlock:
    return ContextBlock(
        item_id=item_id,
        document_id=document_id,
        section_path=section_path,
        text=text,
        token_count=token_count or max(1, len(text.split())),
    )


def make_context(
    *,
    blocks: list[ContextBlock] | None = None,
    citation_map: dict[str, Citation] | None = None,
    conflicts: list[ConflictGroup] | None = None,
    context_id: str = "ctx_test0000000001",
    plan_id: str = "plan_test001",
) -> Context:
    blocks = blocks or []
    if citation_map is None:
        citation_map = {
            block.item_id: _citation(document_id=block.document_id)
            for block in blocks
        }

    token_count = sum(block.token_count for block in blocks)
    return Context(
        context_id=context_id,
        pack_id="ep_test0000000001",
        plan_id=plan_id,
        ordered_blocks=blocks,
        citation_map=citation_map,
        token_count=token_count,
        conflicts=conflicts or [],
        metadata=ContextMetadata(
            items_included=len(blocks),
            items_dropped=0,
            items_compressed=0,
            budget_total=4000,
            budget_used=token_count,
        ),
        created_at="2026-07-14T00:00:00Z",
    )


def make_two_block_context() -> Context:
    block_a = make_block(
        item_id="ei_aaaa000000000001",
        document_id="doc_001",
        text="Adults: 500 mg twice daily. [BNF 4.7.1]",
        section_path="4.7.1",
    )
    block_b = make_block(
        item_id="ei_bbbb000000000002",
        document_id="doc_002",
        text="Avoid in renal impairment (eGFR < 30).",
    )
    citation_map = {
        "ei_aaaa000000000001": _citation(
            document_id="doc_001",
            chunk_id="chunk_01",
            section_title="4.7.1",
            document_title="BNF 2025",
        ),
        "ei_bbbb000000000002": _citation(
            document_id="doc_002",
            chunk_id="chunk_07",
            retrieval_score=0.88,
        ),
    }
    return make_context(blocks=[block_a, block_b], citation_map=citation_map)


class MockLLMEnums:
    SYSTEM = type("EnumValue", (), {"value": "system"})()


class MockLLM(LLMInterface):
    enums = MockLLMEnums()

    def __init__(self, response: str | None = None) -> None:
        self.response = response or json.dumps(
            {
                "answer": (
                    "The recommended adult dose is 500 mg twice daily "
                    "[ei_aaaa000000000001]."
                ),
                "confidence_note": "Based on provided sources.",
            }
        )
        self.call_count = 0
        self.last_chat_history: list | None = None
        self.last_prompt: str | None = None

    def set_generation_model(self, model_id: str) -> None:
        _ = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int) -> None:
        _ = model_id, embedding_size

    def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        *,
        response_mime_type: str | None = None,
        response_schema: dict | None = None,
    ):
        _ = chat_history, max_output_tokens, temperature, response_mime_type, response_schema
        return self.response

    async def generate_text_async(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
        *,
        response_mime_type: str | None = None,
        response_schema: dict | None = None,
    ):
        self.call_count += 1
        self.last_chat_history = chat_history
        self.last_prompt = prompt
        _ = max_output_tokens, temperature, response_mime_type, response_schema
        return self.response

    def embed_text(self, text: str, document_type: str | None = None):
        _ = text, document_type
        return []

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}


@pytest.fixture
def default_config() -> AnswerGenerationConfig:
    return AnswerGenerationConfig(
        system_prompt_template=(
            "Answer from context only. Return JSON with answer and confidence_note."
        )
    )


@pytest.fixture
def sample_context() -> Context:
    return make_two_block_context()


@pytest.fixture
def mock_llm() -> MockLLM:
    return MockLLM()

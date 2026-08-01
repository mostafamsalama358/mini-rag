"""Unit tests for PipelineModeResolver."""

from __future__ import annotations

from types import SimpleNamespace

from services.rag.pipeline.mode_resolver import PipelineModeResolver


def _settings(**overrides):
    base = {
        "RAG_PIPELINE_MODE": "legacy",
        "RAG_PIPELINE_CANARY_PROJECT_IDS": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_resolve_uses_global_mode():
    resolver = PipelineModeResolver()
    assert resolver.resolve(project_id=1, settings=_settings(RAG_PIPELINE_MODE="shadow")) == "shadow"


def test_resolve_project_config_overrides_global():
    resolver = PipelineModeResolver()
    mode = resolver.resolve(
        project_id=1,
        project_config={"pipeline_mode": "unified"},
        settings=_settings(RAG_PIPELINE_MODE="legacy"),
    )
    assert mode == "unified"


def test_resolve_canary_forces_unified():
    resolver = PipelineModeResolver()
    mode = resolver.resolve(
        project_id=42,
        project_config=None,
        settings=_settings(
            RAG_PIPELINE_MODE="legacy",
            RAG_PIPELINE_CANARY_PROJECT_IDS="7,42,99",
        ),
    )
    assert mode == "unified"


def test_resolve_invalid_project_mode_falls_through():
    resolver = PipelineModeResolver()
    mode = resolver.resolve(
        project_id=1,
        project_config={"pipeline_mode": "experimental"},
        settings=_settings(RAG_PIPELINE_MODE="shadow"),
    )
    assert mode == "shadow"


def test_resolve_defaults_to_legacy_on_unknown_global():
    resolver = PipelineModeResolver()
    mode = resolver.resolve(
        project_id=1,
        settings=_settings(RAG_PIPELINE_MODE="wat"),
    )
    assert mode == "legacy"

"""Field-pack → stage config builder (spec 015)."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import yaml

from core.answer_generation.config import (
    AnswerGenerationConfig,
    resolve_answer_generation_config,
)
from core.context_builder.config import (
    ContextBuilderConfig,
    resolve_context_builder_config,
)
from core.evidence_orchestrator.config import (
    EvidenceOrchestratorConfig,
    load_config_from_yaml as load_evidence_config,
    merge_config as merge_evidence_config,
)
from core.retrieval_engine.models import RetrievalEngineConfig
from core.retrieval_engine.policies import (
    ExecutionPolicy,
    PartialResultPolicy,
    TimeoutPolicy,
)
from core.retrieval_planner.models import RetrievalPlannerConfig
from services.FieldRegistry import FieldProfile
from services.rag.pipeline.models import PipelineExecutionContext

_FIELDS_DIR = Path(__file__).resolve().parents[3] / "fields"


def _deep_merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    if not override:
        return copy.deepcopy(base)
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def _domain_key(profile: FieldProfile) -> str:
    return getattr(profile, "domain_key", None) or "generic"


def _profile_overrides(profile: FieldProfile) -> dict[str, Any]:
    cfg = getattr(profile, "config", None)
    return cfg if isinstance(cfg, dict) else {}


class FieldContextAdapter:
    """Builds planner/engine/evidence/context/answer configs from FieldProfile."""

    def __init__(self, fields_dir: Path | None = None) -> None:
        self._fields_dir = Path(fields_dir) if fields_dir else _FIELDS_DIR

    def _merged_module(
        self,
        module_filename: str,
        profile: FieldProfile,
        *,
        config_key: str | None = None,
    ) -> dict[str, Any]:
        domain = _domain_key(profile)
        generic = _load_yaml(self._fields_dir / "generic" / module_filename)
        domain_data = (
            _load_yaml(self._fields_dir / domain / module_filename)
            if domain != "generic"
            else {}
        )
        merged = _deep_merge(generic, domain_data)
        overrides = _profile_overrides(profile)
        if config_key and isinstance(overrides.get(config_key), dict):
            merged = _deep_merge(merged, overrides[config_key])
        return merged

    def build_planner_config(self, profile: FieldProfile) -> RetrievalPlannerConfig:
        data = self._merged_module(
            "retrieval_planning.yaml",
            profile,
            config_key="retrieval_planner",
        )
        # Keep only fields accepted by RetrievalPlannerConfig (extra=forbid).
        allowed = set(RetrievalPlannerConfig.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in allowed}
        return RetrievalPlannerConfig.model_validate(filtered)

    def build_engine_config(self, profile: FieldProfile) -> RetrievalEngineConfig:
        data = self._merged_module(
            "retrieval_engine.yaml",
            profile,
            config_key="retrieval_engine",
        )
        allowed = set(RetrievalEngineConfig.model_fields.keys())
        filtered = {k: v for k, v in data.items() if k in allowed}
        return RetrievalEngineConfig.model_validate(filtered)

    def build_engine_policy(
        self,
        ctx: PipelineExecutionContext,
        profile: FieldProfile,
    ) -> ExecutionPolicy:
        _ = profile
        remaining_ms = max(1, int((ctx.deadline_at - time.perf_counter()) * 1000))
        return ExecutionPolicy(
            timeout=TimeoutPolicy(total_pipeline_ms=remaining_ms),
            partial_result=PartialResultPolicy(allow_partial=True),
        )

    def build_evidence_config(self, profile: FieldProfile) -> EvidenceOrchestratorConfig:
        domain = _domain_key(profile)
        generic_path = self._fields_dir / "generic" / "evidence_orchestrator.yaml"
        base = (
            load_evidence_config(generic_path)
            if generic_path.exists()
            else EvidenceOrchestratorConfig()
        )
        domain_path = self._fields_dir / domain / "evidence_orchestrator.yaml"
        if domain != "generic" and domain_path.exists():
            base = merge_evidence_config(base, load_evidence_config(domain_path))
        overrides = _profile_overrides(profile).get("evidence_orchestrator")
        if isinstance(overrides, dict):
            base = merge_evidence_config(base, overrides)
        return base

    def build_context_config(self, profile: FieldProfile) -> ContextBuilderConfig:
        return resolve_context_builder_config(
            _domain_key(profile),
            _profile_overrides(profile),
        )

    def build_answer_config(self, profile: FieldProfile) -> AnswerGenerationConfig:
        return resolve_answer_generation_config(
            _domain_key(profile),
            _profile_overrides(profile),
        )

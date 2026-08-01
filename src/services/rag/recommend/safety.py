"""Safety Filtering — extensible model; v1 subset active; unknown ≠ safe."""

from __future__ import annotations

from typing import Any

from services.rag.recommend.models import (
    RecommendationCandidate,
    SafetyLabel,
    SafetyOutcomeKind,
)
from services.rag.recommend.pack_access import load_safety_model


def _active_dimensions(model: dict[str, Any]) -> list[str]:
    dims = model.get("dimensions") or {}
    return [name for name, meta in dims.items() if isinstance(meta, dict) and meta.get("active")]


def _label_value(label: SafetyLabel | dict[str, Any] | None, dimension: str) -> str:
    if label is None:
        return "unknown"
    if isinstance(label, SafetyLabel):
        data = label.model_dump()
    else:
        data = dict(label)
    raw = data.get(dimension)
    if raw is None or str(raw).strip() == "":
        return "unknown"
    return str(raw).strip().casefold()


def evaluate_safety(
    label: SafetyLabel | dict[str, Any] | None,
    *,
    population: str | None,
    model: dict[str, Any] | None = None,
) -> tuple[SafetyOutcomeKind, dict[str, str], float]:
    """Return outcome, per-dimension statuses, and safety_fitness in [0,1]."""
    mdl = model or load_safety_model()
    actions = {str(k).casefold(): str(v) for k, v in (mdl.get("actions") or {}).items()}
    active = _active_dimensions(mdl)

    # Map population cue → dimension
    pop = (population or "").strip().casefold()
    needed: list[str] = []
    if any(k in pop for k in ("pregnan", "حمل", "حامل")):
        needed.append("pregnancy")
    if any(k in pop for k in ("breast", "lactat", "رضاع")):
        needed.append("breastfeeding")
    if any(k in pop for k in ("pediatric", "child", "طفل", "اطفال")):
        needed.append("pediatric")
    if any(k in pop for k in ("elderly", "كبير", "مسن")):
        needed.append("elderly")
    if any(k in pop for k in ("renal", "كلى", "كلوي")):
        needed.append("renal_impairment")
    if any(k in pop for k in ("hepatic", "liver", "كبد")):
        needed.append("hepatic_impairment")

    # If population declared, only evaluate overlapping active dims; else soft pass
    dims_to_check = [d for d in needed if d in active]
    if not dims_to_check:
        return "pass", {}, 1.0

    statuses: dict[str, str] = {}
    kinds: list[SafetyOutcomeKind] = []
    for dim in dims_to_check:
        val = _label_value(label, dim)
        statuses[dim] = val
        action = actions.get(val, "demote")
        if action == "exclude":
            kinds.append("exclude")
        elif action == "demote":
            kinds.append("demote" if val != "unknown" else "unknown")
        else:
            kinds.append("pass")

    if "exclude" in kinds:
        outcome: SafetyOutcomeKind = "exclude"
        fitness = 0.0
    elif "unknown" in kinds:
        outcome = "unknown"
        fitness = 0.35
    elif "demote" in kinds:
        outcome = "demote"
        fitness = 0.45
    else:
        outcome = "pass"
        fitness = 1.0
    return outcome, statuses, fitness


def apply_safety_filter(
    candidates: list[RecommendationCandidate],
    *,
    population: str | None,
    model: dict[str, Any] | None = None,
) -> list[RecommendationCandidate]:
    out: list[RecommendationCandidate] = []
    for cand in candidates:
        label_data = cand.metadata.get("safety") or {}
        outcome, statuses, fitness = evaluate_safety(
            label_data, population=population, model=model
        )
        signals = cand.ranking_signals.model_copy(update={"safety_fitness": fitness})
        out.append(
            cand.model_copy(
                update={
                    "safety_outcome": outcome,
                    "safety_dimensions": statuses,
                    "ranking_signals": signals,
                }
            )
        )
    return out

"""Retrieval Planner error hierarchy."""

from __future__ import annotations


class RetrievalPlannerError(Exception):
    """Base error for all Retrieval Planner failures."""


class PlannerConfigError(RetrievalPlannerError):
    """Invalid or incomplete planner configuration."""


class StrategyNotFoundError(RetrievalPlannerError):
    """Requested strategy id is not registered."""


class PlanAssemblyError(RetrievalPlannerError):
    """Failed to assemble a valid RetrievalPlan."""

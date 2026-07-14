"""Unit tests for DefaultTokenBudgetAllocator."""

from __future__ import annotations

from core.context_builder.budget.default_allocator import DefaultTokenBudgetAllocator
from core.context_builder.config import BudgetReservations, ContextBuilderConfig


def test_allocate_returns_window_minus_reservations():
    config = ContextBuilderConfig(
        total_context_window=8000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    )
    allocator = DefaultTokenBudgetAllocator()
    assert allocator.allocate(config) == 6300


def test_allocate_returns_zero_when_reservations_exceed_window():
    config = ContextBuilderConfig(
        total_context_window=1000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    )
    allocator = DefaultTokenBudgetAllocator()
    assert allocator.allocate(config) == 0


def test_allocate_never_returns_negative():
    config = ContextBuilderConfig(
        total_context_window=100,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    )
    allocator = DefaultTokenBudgetAllocator()
    assert allocator.allocate(config) >= 0

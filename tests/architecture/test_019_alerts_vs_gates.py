"""T058 — alerts notify; gates decide."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, read


def test_alerts_notify_gates_decide() -> None:
    text = read(GOV_019 / "alert-catalog.md")
    assert "notify" in text.lower()
    assert "gates decide" in text.lower() or "gate" in text.lower()
    for category in (
        "Threshold Alert",
        "Regression Alert",
        "Trend Alert",
        "Drift Alert",
        "Cost Alert",
        "Latency Alert",
    ):
        assert category in text

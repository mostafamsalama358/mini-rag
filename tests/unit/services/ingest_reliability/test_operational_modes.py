from types import SimpleNamespace

from services.ingest_reliability.models import OperationalMode
from services.ingest_reliability.modes import current_mode, describe_mode


def test_current_mode_and_description():
    s = SimpleNamespace(INGEST_OPERATIONAL_MODE="recovery")
    mode = current_mode(s)
    assert mode == OperationalMode.RECOVERY
    assert "Orphan" in describe_mode(mode)


def test_invalid_mode_defaults_normal():
    s = SimpleNamespace(INGEST_OPERATIONAL_MODE="nope")
    assert current_mode(s) == OperationalMode.NORMAL

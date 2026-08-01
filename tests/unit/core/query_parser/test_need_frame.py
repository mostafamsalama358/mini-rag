"""T015 / NeedFrame validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.query_parser.need_frame import NeedFrame


def test_need_frame_all_optional() -> None:
    nf = NeedFrame()
    assert nf.normalized_need is None
    assert nf.indication_tags == []


def test_need_frame_confidence_bounds() -> None:
    NeedFrame(confidence=0.0)
    NeedFrame(confidence=1.0)
    with pytest.raises(ValidationError):
        NeedFrame(confidence=1.5)

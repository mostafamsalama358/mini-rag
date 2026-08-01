from services.ingest_reliability.models import ParseOutcomeClass
from services.ingest_reliability.parse_bridge import map_extraction_outcome


def test_full_success():
    outcome, _ = map_extraction_outcome({"outcome": "full"}, element_count=3)
    assert outcome == ParseOutcomeClass.SUCCESS


def test_degraded_with_content():
    outcome, reason = map_extraction_outcome(
        {"outcome": "degraded", "reason": "unsupported_structure"},
        element_count=2,
    )
    assert outcome == ParseOutcomeClass.DEGRADED
    assert reason == "unsupported_structure"


def test_empty_success_becomes_failed():
    outcome, _ = map_extraction_outcome({"outcome": "full"}, element_count=0)
    assert outcome == ParseOutcomeClass.FAILED


def test_degraded_empty_fails():
    outcome, _ = map_extraction_outcome({"outcome": "degraded"}, element_count=0)
    assert outcome == ParseOutcomeClass.FAILED

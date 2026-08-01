from services.ingest_reliability.history import append_event, build_history_event


def test_redacts_secrets():
    event = build_history_event(
        job_id="j1",
        correlation_id="c1",
        event_type="failure",
        detail={"api_key": "secret-value", "ok": True},
    )
    assert event["detail"]["api_key"] == "[REDACTED]"
    assert event["detail"]["ok"] is True
    assert event["correlation_id"] == "c1"


def test_append_event_grows_history():
    history: list = []
    append_event(
        history,
        job_id="j1",
        correlation_id="c1",
        event_type="lifecycle",
        detail={"state": "Accepted"},
        stage="admission",
    )
    assert len(history) == 1
    assert history[0]["event_type"] == "lifecycle"

from services.ingest_reliability.checkpoints import is_resume_eligible
from services.ingest_reliability.failures import classify_failure, should_retry
from services.ingest_reliability.models import FailureOwnership


def test_resume_eligibility():
    class CP:
        progress_token = "token-1"

    assert is_resume_eligible(
        checkpoint=CP(), cancelled=False, poisoned=False, within_retry_budget=True
    )
    assert not is_resume_eligible(
        checkpoint=CP(), cancelled=True, poisoned=False, within_retry_budget=True
    )
    assert not is_resume_eligible(
        checkpoint=None, cancelled=False, poisoned=False, within_retry_budget=True
    )


def test_transient_retry():
    f = classify_failure("connection unavailable to storage")
    assert f.kind == "transient"
    assert should_retry(f, attempt=1, max_retries=3)
    assert not should_retry(f, attempt=3, max_retries=3)


def test_permanent_user_input():
    f = classify_failure("unauthorized upload", ownership_hint=FailureOwnership.USER_INPUT)
    assert f.kind == "permanent"
    assert not should_retry(f, attempt=0, max_retries=3)

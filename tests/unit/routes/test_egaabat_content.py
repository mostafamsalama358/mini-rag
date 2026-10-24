from routes.egaabat import celery_status, parse_content_id


def test_content_id_carries_grade_subject_and_attachment():
    parsed = parse_content_id(
        "egaabat:G6:science:textbook:34abbeae-5746-45af-956f-7a00083e456c"
    )
    assert parsed["grade"] == "G6"
    assert parsed["subject"] == "science"
    assert parsed["content_type"] == "textbook"
    assert parsed["attachment_id"] == "34abbeae-5746-45af-956f-7a00083e456c"
    assert parse_content_id("not-a-content-id") == {}


def test_missing_task_stays_processing():
    assert celery_status(None) == "processing"
    assert celery_status("") == "processing"

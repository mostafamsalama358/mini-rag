"""Domain-aware no-context copy (pharmacy vs school)."""

from services.rag.answer_service import _no_context_answer


def test_pharmacy_arabic_mentions_drug():
    text = _no_context_answer("ما جرعة الدواء؟", lang="ar", domain_key="pharmacy")
    assert "دواء" in text


def test_madrsty_arabic_does_not_mention_drug():
    text = _no_context_answer("ما هو علم النفس؟", lang="ar", domain_key="madrsty")
    assert "دواء" not in text
    assert "المادة" in text or "المهارة" in text


def test_generic_english_does_not_mention_drug():
    text = _no_context_answer("What is sampling?", lang="en", domain_key="madrsty")
    assert "drug" not in text.lower()
    assert "subject" in text.lower() or "skill" in text.lower()

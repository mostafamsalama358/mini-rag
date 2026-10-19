"""Visual-order Arabic repair in extracted PDF text."""

from utils.text_cleaning import clean_extracted_text, unflip_visually_reversed_arabic


def test_unflips_reversed_psychology_heading():
    assert unflip_visually_reversed_arabic("سفنلا ملع") == "علم النفس"
    assert clean_extracted_text("سفنلا ملع") == "علم النفس"


def test_preserves_correct_arabic():
    assert clean_extracted_text("علم النفس") == "علم النفس"
    assert clean_extracted_text("الفصل الأول") == "الفصل الأول"


def test_unflips_numbered_reversed_heading():
    assert clean_extracted_text("1. سفنلا ملع") == "1. علم النفس"


def test_preserves_latin_and_mixed_lines():
    french = "Bonjour tout le monde"
    assert clean_extracted_text(french) == french
    mixed = "Chapter Psychology سفنلا ملع"
    assert clean_extracted_text(mixed) == mixed


def test_unflips_per_word_heading_with_al():
    assert clean_extracted_text("لصفلا عبارلا") == "الفصل الرابع"


def test_preserves_years_on_short_reversed_line():
    assert "1990" in unflip_visually_reversed_arabic("سفنلا ملع 1990")


def test_skips_long_paragraphs():
    reversed_words = "سفنلا ملع " * 8
    assert unflip_visually_reversed_arabic(reversed_words.strip()) == reversed_words.strip()

"""Low-quality PDF text-layer detection for hybrid OCR routing."""

from utils.pdf_page_detect import is_low_quality_text_layer


def test_normal_prose_is_not_low_quality():
    text = (
        "This chapter explains sampling methods and how to draw a stratified "
        "random sample from a finite population using a table of random numbers."
    )
    assert is_low_quality_text_layer(text) is False


def test_french_prose_is_not_low_quality():
    text = (
        "Bonjour, comment allez-vous aujourd'hui? Nous apprenons le vocabulaire "
        "de la famille et les expressions de la vie quotidienne a l'ecole."
    )
    assert is_low_quality_text_layer(text) is False


def test_isolated_letter_math_font_is_low_quality():
    text = " ".join(["F", "i", "x", "y"] * 8)
    assert is_low_quality_text_layer(text) is True


def test_replacement_chars_are_low_quality():
    text = "formula " + ("\ufffd" * 4) + " remainder of the page text here"
    assert is_low_quality_text_layer(text) is True

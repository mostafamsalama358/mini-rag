import re
import unicodedata

_AR_CHAR = r"\u0600-\u06ff\u0750-\u077f"
_LATIN_CHAR = r"A-Za-z0-9"
_STANDALONE_PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$", re.MULTILINE)
_BROKEN_ARABIC_FRAGMENT = re.compile(
    rf"(?<=\s[{_AR_CHAR}]) (?=[{_AR_CHAR}]{{1,3}}(?:\s|$|[،.:\)]))"
)
_BROKEN_LATIN_FRAGMENT = re.compile(
    r"(?<=\s[A-Za-z]) (?=[A-Za-z]{1,3}(?:\s|$|[,.:;)]))"
)
_LINE_BREAK_MERGE = re.compile(
    rf"(?<=[{_AR_CHAR}{_LATIN_CHAR}])[\r\n]+(?=[{_AR_CHAR}{_LATIN_CHAR}])"
)
_MULTI_BLANK_LINES = re.compile(r"\n{3,}")
_MULTI_SPACES = re.compile(r"[^\S\n]+")
_ARABIC_WORD = re.compile(rf"[{_AR_CHAR}]+")
_LATIN_WORD = re.compile(r"[A-Za-z]{3,}")
_LTR_RUN = re.compile(r"[A-Za-z0-9٠-٩]+")
_ENUM_PREFIX = re.compile(
    r"^(?P<prefix>\s*(?:[\d٠-٩]+|[IVXivx]+)[.)\-]\s*|[-*•]\s*)"
)
_MAX_UNFLIP_WORDS = 12


def _arabic_char_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(1 for ch in letters if "\u0600" <= ch <= "\u06ff")
    return arabic / len(letters)


def _al_prefix_ratio(text: str) -> float:
    words = _ARABIC_WORD.findall(text)
    if not words:
        return 0.0
    hits = sum(1 for word in words if word.startswith("ال") and len(word) >= 3)
    return hits / len(words)


def _reverse_preserving_ltr(text: str) -> str:
    reversed_text = text[::-1]
    return _LTR_RUN.sub(lambda match: match.group(0)[::-1], reversed_text)


def _reverse_each_arabic_word(text: str) -> str:
    return _ARABIC_WORD.sub(lambda match: match.group(0)[::-1], text)


def _all_arabic_words_have_al(text: str) -> bool:
    words = _ARABIC_WORD.findall(text)
    return bool(words) and all(word.startswith("ال") and len(word) >= 3 for word in words)


def _looks_visually_reversed_arabic(line: str) -> bool:
    """True when a short line is standard Arabic letters in visual order.

    Conservative: skip long paragraphs (they can mix citations and reverse
    digit runs). Correct Arabic is left unchanged.
    """
    words = _ARABIC_WORD.findall(line)
    if not words or len(words) > _MAX_UNFLIP_WORDS:
        return False
    arabic_chars = sum(1 for ch in line if "\u0600" <= ch <= "\u06ff")
    if arabic_chars < 6:
        return False
    if _LATIN_WORD.search(line):
        return False
    if _arabic_char_ratio(line) < 0.55:
        return False
    if _al_prefix_ratio(line) >= 0.25:
        return False
    flipped = _reverse_preserving_ltr(line)
    return _al_prefix_ratio(flipped) >= 0.25


def _unflip_line(line: str) -> str:
    match = _ENUM_PREFIX.match(line)
    prefix = match.group("prefix") if match else ""
    rest = line[len(prefix) :] if prefix else line
    if not _looks_visually_reversed_arabic(rest):
        return line
    words = _ARABIC_WORD.findall(rest)
    per_word = _reverse_each_arabic_word(rest)
    if 2 <= len(words) <= 3 and _all_arabic_words_have_al(per_word):
        return f"{prefix}{per_word}"
    return f"{prefix}{_reverse_preserving_ltr(rest)}"


def unflip_visually_reversed_arabic(text: str) -> str:
    """Undo visual-order Arabic headings (e.g. ``سفنلا ملع`` → ``علم النفس``)."""
    if not text:
        return text
    return "\n".join(_unflip_line(line) for line in text.split("\n"))


def clean_extracted_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unflip_visually_reversed_arabic(text)
    text = _STANDALONE_PAGE_NUMBER.sub("", text)
    text = _LINE_BREAK_MERGE.sub(" ", text)
    text = _BROKEN_ARABIC_FRAGMENT.sub("", text)
    text = _BROKEN_LATIN_FRAGMENT.sub("", text)
    text = _MULTI_BLANK_LINES.sub("\n\n", text)
    text = _MULTI_SPACES.sub(" ", text)

    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()

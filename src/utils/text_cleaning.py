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


def clean_extracted_text(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _STANDALONE_PAGE_NUMBER.sub("", text)
    text = _LINE_BREAK_MERGE.sub(" ", text)
    text = _BROKEN_ARABIC_FRAGMENT.sub("", text)
    text = _BROKEN_LATIN_FRAGMENT.sub("", text)
    text = _MULTI_BLANK_LINES.sub("\n\n", text)
    text = _MULTI_SPACES.sub(" ", text)

    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()

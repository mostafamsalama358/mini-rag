import re

_ARABIC_CHAR = r"[\u0600-\u06ff\u0750-\u077f]"

_SPECIFIC_PATTERNS = [
    re.compile(r"\d"),
    re.compile(
        r"\b(section|chapter|paragraph|part|step|item|appendix|table|figure|clause|schedule)\b",
        re.IGNORECASE,
    ),
    re.compile(rf"{_ARABIC_CHAR}{{2,}}.*\d|\d.*{_ARABIC_CHAR}{{2,}}"),
    re.compile(rf"\b(قسم|فصل|فقرة|بند|ملحق|جدول|خطوة)\b"),
    re.compile(r"[«»\"'].+?[«»\"']"),
]


def is_specific_query(query: str) -> bool:
    """True when the question targets a concrete fact (number, section, quote, etc.)."""
    text = (query or "").strip()
    if not text:
        return False

    for pattern in _SPECIFIC_PATTERNS:
        if pattern.search(text):
            return True

    return False


_FOLLOWUP_PATTERNS = [
    re.compile(
        r"\b(it|its|that|this|those|these|same|above|mentioned|previous|earlier|there)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:^|\s)(?:ده|دي|دا|دول|ه(?:و|ي)|هما|هم)\b|"
        rf"(?:ال(?:سابق|مذكور|موض(?:ح|وح)|سابق(?:ة)?)|(?:اللي|الذي)\s+(?:فات|قلت|ذكرت|قصد))",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:و|also|plus|additionally|كمان|أيضاً|además)\s", re.IGNORECASE),
]


def is_followup_query(query: str) -> bool:
    """True when the question clearly refers to the prior turn, not a new standalone topic."""
    text = (query or "").strip()
    if not text:
        return False

    return any(pattern.search(text) for pattern in _FOLLOWUP_PATTERNS)


def select_chat_history_messages(
    prior_messages,
    *,
    query: str,
    mode: str = "auto",
    user_role: str,
    assistant_roles: tuple[str, ...] = ("assistant", "model", "CHATBOT"),
    max_turns: int = 4,
):
    if not prior_messages:
        return []

    normalized_mode = (mode or "auto").strip().lower()

    if normalized_mode == "minimal":
        return []

    if normalized_mode == "full":
        return list(prior_messages)

    user_messages = [message for message in prior_messages if message.role == user_role]

    if normalized_mode == "user_only":
        return user_messages[-max_turns:]

    # auto: standalone RAG questions should not replay prior user turns.
    # Replaying them without the current question in the prompt causes off-by-one answers.
    if not is_followup_query(query):
        return []

    if len(user_messages) >= 2:
        return user_messages[-2:]

    return user_messages[-1:] if user_messages else []

"""Explanation Policy for recommend/compare answers (Feature 020)."""

from __future__ import annotations

import re

_HIDDEN_SCORE_PATTERNS = (
    re.compile(r"\bhidden\s+score", re.I),
    re.compile(r"\brank(?:ing)?\s+weight", re.I),
    re.compile(r"\binternal\s+score", re.I),
    re.compile(r"\bsignal_weights?\b", re.I),
    re.compile(r"\brecommendation_score\s*=", re.I),
)

_UNSUPPORTED_SUPERIORITY = re.compile(
    r"\b(clinically superior|definitively better|always better than)\b",
    re.I,
)


def violates_hidden_score_policy(text: str) -> bool:
    return any(p.search(text or "") for p in _HIDDEN_SCORE_PATTERNS)


def claims_unsupported_superiority(text: str) -> bool:
    return bool(_UNSUPPORTED_SUPERIORITY.search(text or ""))


def medical_advice_disclaimer(*, language: str = "en") -> str:
    if (language or "").startswith("ar"):
        return (
            "هذه توصية مبنية على مصادر الفهرس المتاح وليست وصفة طبية. "
            "استشر صيدليًا أو طبيبًا عند الحاجة."
        )
    return (
        "This is a corpus-bounded recommendation, not a medical prescription. "
        "Consult a pharmacist or physician when needed."
    )


def sanitize_recommend_answer(text: str, *, language: str = "en") -> str:
    """Best-effort strip of policy-violating phrases; does not invent clinical claims."""
    out = text or ""
    if violates_hidden_score_policy(out):
        out = _HIDDEN_SCORE_PATTERNS[0].sub("[evidence-based rationale]", out)
        for p in _HIDDEN_SCORE_PATTERNS[1:]:
            out = p.sub("", out)
    disclaimer = medical_advice_disclaimer(language=language)
    if disclaimer not in out:
        out = out.rstrip() + "\n\n" + disclaimer
    return out


RECOMMEND_CAPABILITY_INSTRUCTIONS = """
When recommend_mode is active:
- Rank options using retrieved evidence and indication fit only.
- Do NOT mention hidden scores, internal weights, or ranking formulas.
- Do NOT invent clinical superiority without explicit evidence in context.
- Distinguish recommendation (corpus decision support) from medical advice.
- Always cite source block IDs for recommended claims.
- Keep Latin brand names; answer in the user's language.
""".strip()

RECOMMEND_COMPARE_INSTRUCTIONS = """
When comparing need-matched products:
- Compare only on fields supported by retrieved evidence (indication, safety, interactions).
- Do not claim clinical superiority without evidence.
- Do not explain using hidden ranking scores.
""".strip()

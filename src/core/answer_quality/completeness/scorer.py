"""Keyword overlap completeness scorer (anti-stuffing hardened)."""

from __future__ import annotations

import re

from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.interfaces import ICompletenessScorer
from core.answer_quality.models import CompletenessResult, GoldenTestFixture

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "if",
        "with",
        "at",
        "by",
        "from",
        "as",
        "be",
        "this",
        "that",
        "it",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "about",
        "into",
        "than",
    }
)

# Meta / table-of-contents phrasing — not an answer.
_TOPIC_SUMMARY_RE = re.compile(
    r"\b("
    r"this document discusses|this (?:article|text|section|page) (?:discusses|covers|describes|mentions)"
    r"|general .+ information"
    r"|information for patients"
    r"|information about"
    r"|discusses? .+ and .+"
    r"|covers? (?:topics?|areas?|aspects?)"
    r"|the following (?:topics?|items?|points?)"
    r"|provides? (?:an? )?(?:overview|summary|information)"
    r"|topics? include|aspects? include|areas? include"
    r")\b",
    re.IGNORECASE,
)

# Assertive / instructional cues that mark a real claim.
# Intentionally excludes bare "dose/dosage/mg" — those appear in stuffed
# topic lists ("dosage warnings") without answering the question.
_CLAIM_CUE_RE = re.compile(
    r"\b("
    r"is|are|was|were|been|being|am|"
    r"must|shall|may|might|cannot|can't|"
    r"take|taken|taking|avoid|avoided|avoiding|"
    r"contraindicated|recommended|recommend|"
    r"not|never|do\s+not|does\s+not|did\s+not|"
    r"store|stored|exceed|exceeds|exceeded|"
    r"increase|increases|increased|potentiate|potentiates|"
    r"associate|associated|use|used|using|"
    r"start|started|monitor|monitored|"
    r"state|states|stated|disagree|disagrees|"
    r"require|requires|required|need|needs|"
    r"cause|causes|caused|"
    r"include|includes|including|"
    r"below|under|over|above|per|every"
    r")\b",
    re.IGNORECASE,
)

# Meta verbs that alone do not constitute answering the question.
_META_CUE_RE = re.compile(
    r"\b("
    r"discuss(?:es|ed|ing)?|cover(?:s|ed|ing)?|describe(?:s|d)?|"
    r"mention(?:s|ed|ing)?|address(?:es|ed|ing)?|"
    r"provide(?:s|d)?|contain(?:s|ed|ing)?|list(?:s|ed|ing)?|"
    r"overview|summary|information|topics?|aspects?"
    r")\b",
    re.IGNORECASE,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_CITATION_RE = re.compile(r"\[\s*ei_[0-9a-f]{16}\s*\]", re.IGNORECASE)

# Facet-token share of answer tokens above this → suspect stuffing.
_STUFFING_FACET_RATIO = 0.55
# Minimum claim-cue hits expected in a non-stuffed multi-facet answer.
_MIN_CLAIM_CUES_MULTI_FACET = 1


def _effective_completeness_threshold(
    fixture: GoldenTestFixture,
    config: AnswerQualityConfig,
) -> float:
    if fixture.thresholds is not None and fixture.thresholds.completeness is not None:
        return fixture.thresholds.completeness
    if config.global_thresholds.completeness is not None:
        return config.global_thresholds.completeness
    return 0.7


def _stem(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es") and not token.endswith("ness"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    return token


def _tokenise(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {
        _stem(token)
        for token in tokens
        if token not in _STOP_WORDS and len(token) > 1
    }


def _strip_citations(answer: str) -> str:
    return _CITATION_RE.sub(" ", answer)


def _sentences(answer: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(answer) if s.strip()]
    return parts or ([answer.strip()] if answer.strip() else [])


def _is_topic_summary(answer: str) -> bool:
    return bool(_TOPIC_SUMMARY_RE.search(answer))


def _has_claim_shape(sentence: str) -> bool:
    """True when the sentence asserts a fact / instruction, not a TOC blurb."""
    if _TOPIC_SUMMARY_RE.search(sentence):
        return False

    # Navigational: "section covers warfarin and peptic ulcer" is a real answer.
    if re.search(r"\bcovers?\b", sentence, re.IGNORECASE):
        if re.search(
            r"\b(topics?|aspects?|information|overview|summary)\b",
            sentence,
            re.IGNORECASE,
        ):
            return False
        return True

    # Meta framing without an assertive predicate never counts as coverage.
    if _META_CUE_RE.search(sentence) and not _CLAIM_CUE_RE.search(sentence):
        return False
    if _META_CUE_RE.search(sentence) and not re.search(
        r"\b(is|are|must|should|shall|not|never|take|avoid|"
        r"contraindicated|recommended|store|exceed|do\s+not|include|includes)\b",
        sentence,
        re.IGNORECASE,
    ):
        return False
    if _CLAIM_CUE_RE.search(sentence):
        return True
    # Numeric facts (dosing tables) count as claims even with terse phrasing.
    return bool(re.search(r"\d", sentence))


def _is_noun_list_dump(answer: str) -> bool:
    """Comma-heavy answers with almost no claim cues are typically stuffing."""
    if _CLAIM_CUE_RE.search(answer):
        return False
    commas = answer.count(",")
    and_joins = len(re.findall(r"\band\b", answer, flags=re.IGNORECASE))
    if commas + and_joins >= 3:
        return True
    if commas >= 2:
        return True
    return False


def _facet_token_pool(facets: list[str]) -> set[str]:
    pool: set[str] = set()
    for facet in facets:
        pool |= _tokenise(facet)
    return pool


def _looks_like_keyword_stuffing(answer: str, facets: list[str]) -> bool:
    """Structural anti-gaming: high facet density + weak claim structure."""
    cleaned = _strip_citations(answer)
    if _is_topic_summary(cleaned) or _is_noun_list_dump(cleaned):
        return True

    sentences = _sentences(cleaned)
    has_claim_sentence = any(_has_claim_shape(s) for s in sentences)
    # Real claim sentences (incl. navigational "section covers X") are scored
    # per-facet below; do not fail the whole answer as stuffing.
    if has_claim_sentence:
        return False

    answer_tokens = _tokenise(cleaned)
    facet_tokens = _facet_token_pool(facets)
    if not answer_tokens or not facet_tokens:
        return False

    facet_ratio = len(answer_tokens & facet_tokens) / len(answer_tokens)
    claim_hits = len(_CLAIM_CUE_RE.findall(cleaned))
    meta_hits = len(_META_CUE_RE.findall(cleaned))

    # Most of the answer is just facet keywords restated.
    if facet_ratio >= _STUFFING_FACET_RATIO and claim_hits < _MIN_CLAIM_CUES_MULTI_FACET:
        return True
    # Meta language dominates over claims while facets are packed in.
    if meta_hits >= 2 and claim_hits <= meta_hits and facet_ratio >= 0.35:
        return True
    # Multi-facet answers must contain at least one real claim cue.
    if len(facets) >= 2 and claim_hits == 0 and not re.search(r"\d", cleaned):
        return True
    return False


def _question_addressed(question: str, answer: str) -> bool:
    """Reject empty / off-topic answers; allow grounded answers that omit the entity name."""
    q_tokens = _tokenise(question)
    a_tokens = _tokenise(answer)
    if not a_tokens:
        return False
    if not q_tokens:
        return True
    if q_tokens & a_tokens:
        return True
    return len(a_tokens) >= 4 and bool(re.search(r"\d", answer))


def _facet_covered(
    facet: str,
    answer: str,
    overlap_threshold: float,
) -> bool:
    """Facet counts only inside a claim-shaped sentence (not a topic list)."""
    facet_tokens = _tokenise(facet)
    if not facet_tokens:
        return False

    for sentence in _sentences(answer):
        sent_tokens = _tokenise(sentence)
        if not sent_tokens:
            continue
        facet_overlap = len(facet_tokens & sent_tokens) / len(facet_tokens)
        if facet_overlap < overlap_threshold:
            continue
        if not _has_claim_shape(sentence):
            continue
        return True
    return False


class KeywordCompletenessScorer(ICompletenessScorer):
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        config: AnswerQualityConfig,
    ) -> CompletenessResult:
        facets = fixture.expected_answer_facets
        if not facets or answer_result.no_answer:
            return CompletenessResult(
                question_id=fixture.question_id,
                completeness_score=None,
                not_applicable=True,
                passed=True,
            )

        answer = _strip_citations(answer_result.answer)

        if (
            _looks_like_keyword_stuffing(answer, list(facets))
            or not _question_addressed(fixture.question, answer)
        ):
            return CompletenessResult(
                question_id=fixture.question_id,
                completeness_score=0.0,
                covered_facets=[],
                uncovered_facets=list(facets),
                not_applicable=False,
                passed=False,
            )

        covered: list[str] = []
        uncovered: list[str] = []
        for facet in facets:
            if _facet_covered(
                facet,
                answer,
                config.completeness_overlap_threshold,
            ):
                covered.append(facet)
            else:
                uncovered.append(facet)

        score = len(covered) / len(facets)
        threshold = _effective_completeness_threshold(fixture, config)
        passed = score >= threshold

        return CompletenessResult(
            question_id=fixture.question_id,
            completeness_score=score,
            covered_facets=covered,
            uncovered_facets=uncovered,
            not_applicable=False,
            passed=passed,
        )

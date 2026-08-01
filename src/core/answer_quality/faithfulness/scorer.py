"""Text-matching faithfulness scorer."""

from __future__ import annotations

import re

from core.answer_generation.citation.item_id_formatter import _ITEM_ID_PATTERN
from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.interfaces import IFaithfulnessScorer
from core.answer_quality.models import FaithfulnessResult, GoldenTestFixture
from core.context_builder.models import Context

# Numbers with optional unit; do not match bare hex / citation fragments.
_NUMBER_PATTERN = re.compile(
    r"(?<![a-z0-9_])(\d+(?:[.,]\d+)?(?:\s*(?:mg|mcg|g|kg|ml|mL|%|hours?|hrs?|days?|weeks?|months?|years?|tablets?|capsules?))?)\b",
    re.IGNORECASE,
)
_TITLE_CASE_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
_QUOTED_PATTERN = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_CITATION_MARKER = re.compile(
    r"\[\s*ei_[0-9a-f]{16}\s*\]|" + _ITEM_ID_PATTERN.pattern,
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
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
        "you",
        "should",
        "may",
        "can",
        "will",
        "not",
        "no",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "when",
        "where",
        "what",
        "which",
        "who",
        "how",
        "than",
        "then",
        "also",
        "into",
        "your",
        "their",
        "our",
        "any",
        "all",
    }
)
# Lexical grounding floor for prose claims without extractable number/quote spans.
_PROSE_OVERLAP_THRESHOLD = 0.35


def _effective_faithfulness_threshold(
    fixture: GoldenTestFixture,
    config: AnswerQualityConfig,
) -> float:
    if fixture.thresholds is not None and fixture.thresholds.faithfulness is not None:
        return fixture.thresholds.faithfulness
    if config.global_thresholds.faithfulness is not None:
        return config.global_thresholds.faithfulness
    return 0.8


def _strip_citation_markers(answer: str) -> str:
    return _CITATION_MARKER.sub(" ", answer)


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOP_WORDS and len(token) > 1
    }


def _extract_claim_spans(answer: str) -> list[str]:
    spans: list[str] = []
    for match in _NUMBER_PATTERN.finditer(answer):
        spans.append(match.group(1).strip())
    for match in _TITLE_CASE_PATTERN.finditer(answer):
        spans.append(match.group(0).strip())
    for match in _QUOTED_PATTERN.finditer(answer):
        quoted = match.group(1) or match.group(2)
        if quoted:
            spans.append(quoted.strip())
    return spans


def _span_supported(span: str, source_corpus: str) -> bool:
    lowered = span.lower().strip()
    if not lowered:
        return True
    if lowered in source_corpus:
        return True
    # Unit-tolerant numeric match: "325 mg" vs "325mg" / corpus "325 mg".
    compact = re.sub(r"\s+", "", lowered)
    corpus_compact = re.sub(r"\s+", "", source_corpus)
    if compact in corpus_compact:
        return True
    tokens = _tokenize(span)
    if not tokens:
        return False
    corpus_tokens = _tokenize(source_corpus)
    return tokens.issubset(corpus_tokens)


def _prose_grounding_score(answer: str, source_corpus: str) -> tuple[float, list[str]]:
    """Score qualitative sentences by content-token overlap with context.

    Returns (score, unsupported_sentence_snippets). Empty checkable prose →
    score 0.0 (fail-closed) so fabricated qualitative answers cannot pass
    with a perfect score when no number/quote spans were extracted.
    """
    sentences = [
        part.strip()
        for part in _SENTENCE_SPLIT.split(answer)
        if part.strip()
    ]
    if not sentences:
        sentences = [answer.strip()] if answer.strip() else []

    if not sentences:
        return 0.0, ["<empty answer>"]

    corpus_tokens = _tokenize(source_corpus)
    if not corpus_tokens:
        return 0.0, ["<empty context>"]

    unsupported: list[str] = []
    supported = 0
    checked = 0
    for sentence in sentences:
        sent_tokens = _tokenize(sentence)
        if len(sent_tokens) < 3:
            continue
        checked += 1
        overlap = len(sent_tokens & corpus_tokens) / len(sent_tokens)
        if overlap >= _PROSE_OVERLAP_THRESHOLD:
            supported += 1
        else:
            snippet = sentence if len(sentence) <= 120 else sentence[:117] + "..."
            unsupported.append(snippet)

    if checked == 0:
        # Short answers: require majority of content tokens to appear in corpus.
        answer_tokens = _tokenize(answer)
        if not answer_tokens:
            return 0.0, ["<no content tokens>"]
        overlap = len(answer_tokens & corpus_tokens) / len(answer_tokens)
        if overlap >= _PROSE_OVERLAP_THRESHOLD:
            return 1.0, []
        return overlap, [answer.strip()[:120]]

    return supported / checked, unsupported


class TextFaithfulnessScorer(IFaithfulnessScorer):
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        context: Context,
        config: AnswerQualityConfig,
    ) -> FaithfulnessResult:
        if (
            answer_result.no_answer
            or not context.ordered_blocks
            or not answer_result.answer.strip()
        ):
            return FaithfulnessResult(
                question_id=fixture.question_id,
                faithfulness_score=None,
                not_applicable=True,
                passed=True,
            )

        source_corpus = " ".join(
            block.text.lower() for block in context.ordered_blocks
        )
        cleaned_answer = _strip_citation_markers(answer_result.answer)
        spans = _extract_claim_spans(cleaned_answer)
        unsupported = [
            span for span in spans if not _span_supported(span, source_corpus)
        ]

        if spans:
            score = 1.0 - (len(unsupported) / len(spans))
            total_checked = len(spans)
        else:
            # Fail-closed for qualitative-only answers (no number/quote spans).
            # Regex span matching alone cannot see fabricated prose claims.
            score, unsupported = _prose_grounding_score(cleaned_answer, source_corpus)
            total_checked = max(len(_tokenize(cleaned_answer)), 1)

        threshold = _effective_faithfulness_threshold(fixture, config)
        passed = score >= threshold

        return FaithfulnessResult(
            question_id=fixture.question_id,
            faithfulness_score=score,
            unsupported_claims=unsupported,
            total_spans_checked=total_checked,
            not_applicable=False,
            passed=passed,
        )

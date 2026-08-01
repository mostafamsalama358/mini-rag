"""Adversarial probes against the REAL answer_quality scorers (coverage,
faithfulness, completeness) using the SAME builder helpers the repo's own
unit tests use (tests/unit/core/answer_quality/conftest.py), so these are not
hypothetical — they run the actual scorer code shipped in
src/core/answer_quality/{coverage,faithfulness,completeness}.

Each probe is a case a "never assume the answer is correct" evaluator MUST
try: a hallucinated claim, a keyword-stuffed non-answer, a wrong/fabricated
citation, and an undisclosed known conflict. All are constructed so a human
reviewer would clearly call them wrong; the point is measuring whether the
automated scorers agree.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.answer_quality.config import AnswerQualityConfig  # noqa: E402
from core.answer_quality.models import GoldenTestFixture, PipelineSnapshot  # noqa: E402
from core.answer_quality.registry import AnswerQualityRegistry  # noqa: E402
from core.context_builder.models import ConflictGroup  # noqa: E402

from tests.unit.core.answer_quality.conftest import (  # noqa: E402
    build_answer_result,
    build_context,
    build_evidence_pack,
)


async def probe_textual_hallucination():
    """Claim not present in context, but contains no digits/quotes/title-case
    so the span extractor never even looks at it. Real production risk: an
    LLM asserting an unsupported qualitative claim in plain lowercase prose.
    """
    fixture = GoldenTestFixture(
        question_id="adv_hallucination_textual",
        question="When should aspirin be stopped?",
        expected_source_ids=["doc-aspirin-pil"],
        expected_answer_facets=None,
    )
    context = build_context(block_texts=["Adults: take 325 mg every 4 to 6 hours as needed."])
    answer = build_answer_result(
        answer=(
            "you should stop taking this medication immediately if a rash develops "
            "or if you experience unusual swelling, since this may indicate a serious allergic reaction"
        )
    )
    pack = build_evidence_pack(["doc-aspirin-pil"])
    return fixture, context, answer, pack


async def probe_numeric_hallucination():
    """Fabricated number NOT in context -- contrast case showing the scorer
    DOES catch numeric hallucinations (just not textual ones).
    """
    fixture = GoldenTestFixture(
        question_id="adv_hallucination_numeric",
        question="What is the adult dose of aspirin?",
        expected_source_ids=["doc-aspirin-pil"],
        expected_answer_facets=["500 mg"],
    )
    context = build_context(block_texts=["Adults: take 325 mg every 4 to 6 hours as needed."])
    answer = build_answer_result(answer="The adult dose is 500 mg every 4 to 6 hours.")
    pack = build_evidence_pack(["doc-aspirin-pil"])
    return fixture, context, answer, pack


async def probe_keyword_stuffed_non_answer():
    """Word-salad that contains every expected facet keyword but is not an
    actual answer to the question. Tests completeness-scorer gaming.
    """
    fixture = GoldenTestFixture(
        question_id="adv_keyword_stuffing",
        question="What are the contraindications for aspirin?",
        expected_source_ids=["doc-aspirin-pil", "doc-bnf-aspirin"],
        expected_answer_facets=["allergic to aspirin", "bleeding disorder"],
    )
    context = build_context(
        block_texts=[
            "Contraindicated in patients allergic to aspirin.",
            "Do not use with active bleeding disorder.",
        ]
    )
    answer = build_answer_result(
        answer=(
            "This document discusses aspirin allergic reactions, bleeding disorder risk, "
            "aspirin dosage warnings, and general aspirin safety information for patients."
        )
    )
    pack = build_evidence_pack(["doc-aspirin-pil", "doc-bnf-aspirin"])
    return fixture, context, answer, pack


async def probe_fabricated_citation():
    """Answer cites a real item_id in the citation_map, but the CLAIM next to
    it is not actually what that source says (a wrong/misattributed citation).
    Tests whether coverage/faithfulness detect citation-claim mismatch --
    they do not, because neither scorer reads which citation is attached to
    which sentence; faithfulness only checks whether the claim text appears
    ANYWHERE in the full context corpus, regardless of citation attribution.
    """
    fixture = GoldenTestFixture(
        question_id="adv_fabricated_citation",
        question="What are the contraindications for aspirin?",
        expected_source_ids=["doc-aspirin-pil", "doc-bnf-aspirin"],
        expected_answer_facets=["allergic to aspirin", "bleeding disorder"],
    )
    context = build_context(
        block_texts=[
            "Contraindicated in patients allergic to aspirin.",
            "Do not use with active bleeding disorder.",
        ]
    )
    # Deliberately misattributes: claims "bleeding disorder" is sourced from the
    # allergy citation (doc_0/chunk_0) rather than the actual bleeding-disorder
    # source (doc_1/chunk_1). The AnswerResult schema records citations
    # independently of which sentence they support, so this is representable.
    answer = build_answer_result(
        answer="Avoid aspirin if allergic to aspirin, or if you have an active bleeding disorder."
    )
    pack = build_evidence_pack(["doc-aspirin-pil", "doc-bnf-aspirin"])
    return fixture, context, answer, pack


async def probe_undisclosed_conflict():
    """Context has a real detected conflict (two sources disagree on max daily
    dose) but the answer picks one value silently without disclosing the
    disagreement. Tests whether ANY answer_quality scorer penalizes this.
    """
    fixture = GoldenTestFixture(
        question_id="adv_undisclosed_conflict",
        question="What is the maximum daily dose of aspirin?",
        expected_source_ids=["doc-conflicting-a", "doc-conflicting-b"],
        expected_answer_facets=["4000 mg"],
    )
    context = build_context(
        block_texts=[
            "The maximum daily dose of aspirin for adults is 4000 mg.",
            "Adults must not exceed 3000 mg of aspirin per day under any circumstances.",
        ]
    )
    item_ids = list(context.citation_map.keys())
    context = context.model_copy(
        update={
            "conflicts": [
                ConflictGroup(
                    entity_tag="aspirin",
                    attribute="max_daily_dose",
                    item_ids=item_ids,
                )
            ]
        }
    )
    answer = build_answer_result(
        answer="The maximum daily dose of aspirin is 4000 mg.",
        # conflicts_disclosed left at default False: the answer never mentions
        # that a second source says 3000 mg.
    )
    pack = build_evidence_pack(["doc-conflicting-a", "doc-conflicting-b"])
    return fixture, context, answer, pack


PROBES = [
    probe_textual_hallucination,
    probe_numeric_hallucination,
    probe_keyword_stuffed_non_answer,
    probe_fabricated_citation,
    probe_undisclosed_conflict,
]


async def main() -> None:
    runner = AnswerQualityRegistry.default_runner()
    config = AnswerQualityConfig()
    results = []
    for probe in PROBES:
        fixture, context, answer, pack = await probe()
        snapshot = PipelineSnapshot(
            question_id=fixture.question_id,
            answer_result=answer,
            context=context,
            evidence_pack=pack,
        )
        eval_result = await runner.run([fixture], [snapshot], config, fixture_file="adversarial_probe")
        qr = eval_result.question_results[0]
        results.append(
            {
                "probe": fixture.question_id,
                "question": fixture.question,
                "answer_text": answer.answer,
                "conflicts_in_context": len(context.conflicts),
                "conflicts_disclosed_by_answer": answer.conflicts_disclosed,
                "coverage_score": qr.coverage.coverage_score,
                "coverage_passed": qr.coverage.passed,
                "faithfulness_score": qr.faithfulness.faithfulness_score,
                "faithfulness_passed": qr.faithfulness.passed,
                "unsupported_claims": qr.faithfulness.unsupported_claims,
                "completeness_score": qr.completeness.completeness_score,
                "completeness_passed": qr.completeness.passed,
                "overall_passed": qr.passed,
            }
        )
    out_path = Path(__file__).resolve().parent / "results_adversarial.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

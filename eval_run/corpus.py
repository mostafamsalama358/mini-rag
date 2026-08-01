"""Labeled synthetic corpus + query set for end-to-end RAG evaluation.

IMPORTANT: This corpus was authored specifically for this evaluation because the
in-repo golden dataset (tests/fixtures/answer_quality/generic_golden.yaml) has
only 3 fixtures and no relevance judgments usable for IR metrics (Recall@k,
Precision@k, MRR, NDCG). It is intentionally small (documents + chunks) so
relevance can be hand-labeled with full confidence, and intentionally covers
gap categories identified as missing from the existing golden set: multi-hop,
conflicting evidence, near-duplicate content, distractor/irrelevant content,
unanswerable questions, and table/numeric content.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CorpusChunk:
    chunk_id: str
    doc_id: str
    text: str
    section_path: list[str] = field(default_factory=list)


CORPUS: list[CorpusChunk] = [
    # doc-aspirin-pil: primary product leaflet
    CorpusChunk("c1", "doc-aspirin-pil", "Adults: take 325 mg every 4 to 6 hours as needed for pain. Do not exceed 4000 mg in 24 hours.", ["Dosage"]),
    CorpusChunk("c2", "doc-aspirin-pil", "Contraindicated in patients allergic to aspirin or other NSAIDs.", ["Contraindications"]),
    CorpusChunk("c3", "doc-aspirin-pil", "Store below 25 degrees Celsius in a dry place away from direct sunlight.", ["Storage"]),
    CorpusChunk("c4", "doc-aspirin-pil", "Common side effects include stomach upset, heartburn, and nausea.", ["Side Effects"]),
    # doc-bnf-aspirin: formulary reference, contraindications + interactions
    CorpusChunk("c5", "doc-bnf-aspirin", "Do not use aspirin in patients with an active bleeding disorder.", ["Contraindications"]),
    CorpusChunk("c6", "doc-bnf-aspirin", "Concurrent use of aspirin with warfarin significantly increases the risk of bleeding.", ["Interactions"]),
    CorpusChunk("c7", "doc-bnf-aspirin", "Aspirin should be used with caution in patients with a history of peptic ulcer disease.", ["Precautions"]),
    # doc-paediatric-guidance: pediatric-specific
    CorpusChunk("c8", "doc-paediatric-guidance", "Aspirin is not recommended in paediatric patients under 16 years of age.", ["Paediatric Use"]),
    CorpusChunk("c9", "doc-paediatric-guidance", "Aspirin use in children and teenagers has been associated with Reye's syndrome, a rare but serious condition.", ["Paediatric Use"]),
    # doc-warfarin-monograph: separate document, corroborates interaction (multi-hop target)
    CorpusChunk("c10", "doc-warfarin-monograph", "Warfarin has a narrow therapeutic index; NSAIDs and aspirin potentiate its anticoagulant effect.", ["Drug Interactions"]),
    CorpusChunk("c11", "doc-warfarin-monograph", "Monitor INR closely when initiating or discontinuing aspirin in patients on warfarin therapy.", ["Monitoring"]),
    # doc-ibuprofen-pil: distractor-adjacent (different drug, some lexical overlap)
    CorpusChunk("c12", "doc-ibuprofen-pil", "Adults: take 200 mg to 400 mg every 4 to 6 hours as needed. Do not exceed 1200 mg in 24 hours.", ["Dosage"]),
    CorpusChunk("c13", "doc-ibuprofen-pil", "Ibuprofen is contraindicated in the third trimester of pregnancy.", ["Contraindications"]),
    # doc-legal-disclaimer: pure distractor, no pharmacology content at all
    CorpusChunk("c14", "doc-legal-disclaimer", "This document is provided for informational purposes only and does not constitute legal advice.", ["Disclaimer"]),
    CorpusChunk("c15", "doc-legal-disclaimer", "All trademarks referenced herein are the property of their respective owners.", ["Trademarks"]),
    # doc-aspirin-dose-table: tabular / structured content
    CorpusChunk("c16", "doc-aspirin-dose-table", "Dosing table by age band: 12-15 years: 250-500 mg every 4-6 hours (max 4 doses/day). 16+ years: 300-900 mg every 4-6 hours (max 4000 mg/day).", ["Dosing Table"]),
    # doc-conflicting-a / doc-conflicting-b: deliberately contradicting max daily dose (conflict test)
    CorpusChunk("c17", "doc-conflicting-a", "The maximum daily dose of aspirin for adults is 4000 mg.", ["Maximum Dose"]),
    CorpusChunk("c18", "doc-conflicting-b", "Adults must not exceed 3000 mg of aspirin per day under any circumstances.", ["Maximum Dose"]),
    # doc-aspirin-pil-duplicate: near-duplicate of c1 (duplicate retrieval test)
    CorpusChunk("c19", "doc-aspirin-pil-duplicate", "Adults: take 325 mg every 4 to 6 hours as needed for pain relief. Do not exceed 4000 mg within 24 hours.", ["Dosage"]),
    # doc-storage-extended: near-duplicate-ish of c3 but different doc
    CorpusChunk("c20", "doc-storage-extended", "Keep the medication stored below 25 degrees Celsius, in a dry location, protected from sunlight.", ["Storage"]),
]

CORPUS_BY_ID = {c.chunk_id: c for c in CORPUS}


@dataclass(frozen=True)
class EvalQuery:
    query_id: str
    text: str
    category: str  # factual | comparative | procedural | tabular | navigational | multi_hop | ambiguous | unanswerable | conflicting
    relevant_chunk_ids: list[str]
    expected_intent: str  # planner IntentCategory this SHOULD resolve to
    expected_source_doc_ids: list[str]
    expected_answer_facets: list[str]
    field: str = "dosage"
    operation: str = "lookup"
    entity: str | None = "aspirin"
    good_answer: str = ""
    notes: str = ""


QUERIES: list[EvalQuery] = [
    EvalQuery(
        query_id="q_adult_dose",
        text="What is the adult dose of aspirin?",
        category="factual",
        relevant_chunk_ids=["c1"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-aspirin-pil"],
        expected_answer_facets=["325 mg", "every 4 to 6 hours"],
        good_answer="The adult dose is 325 mg every 4 to 6 hours [[CITE0]].",
    ),
    EvalQuery(
        query_id="q_contraindications",
        text="What are the contraindications for aspirin?",
        category="factual",
        relevant_chunk_ids=["c2", "c5"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-aspirin-pil", "doc-bnf-aspirin"],
        expected_answer_facets=["allergic to aspirin", "bleeding disorder"],
        good_answer="Avoid aspirin if allergic to aspirin or NSAIDs [[CITE0]], or if you have an active bleeding disorder [[CITE1]].",
    ),
    EvalQuery(
        query_id="q_children",
        text="Can children take aspirin?",
        category="factual",
        relevant_chunk_ids=["c8", "c9"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-paediatric-guidance"],
        expected_answer_facets=["not recommended", "Reye's syndrome"],
        good_answer="Aspirin is not recommended for children [[CITE0]] due to the risk of Reye's syndrome [[CITE1]].",
    ),
    EvalQuery(
        query_id="q_multihop_warfarin",
        text="Is it safe to take aspirin together with warfarin, and why?",
        category="multi_hop",
        relevant_chunk_ids=["c6", "c10", "c11"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-bnf-aspirin", "doc-warfarin-monograph"],
        expected_answer_facets=["bleeding", "anticoagulant", "INR"],
        field="interactions",
        good_answer=(
            "No. Aspirin combined with warfarin significantly increases bleeding risk [[CITE0]] "
            "because aspirin potentiates warfarin's anticoagulant effect [[CITE1]]; "
            "INR should be monitored closely [[CITE2]]."
        ),
        notes="Requires synthesizing across 2 separate documents (bnf-aspirin + warfarin-monograph).",
    ),
    EvalQuery(
        query_id="q_compare_aspirin_ibuprofen_dose",
        text="Compare the adult dose of aspirin versus ibuprofen.",
        category="comparative",
        relevant_chunk_ids=["c1", "c12"],
        expected_intent="comparative",
        expected_source_doc_ids=["doc-aspirin-pil", "doc-ibuprofen-pil"],
        expected_answer_facets=["325 mg", "200 mg to 400 mg"],
        entity="aspirin",
        good_answer="Aspirin: 325 mg every 4-6 hours [[CITE0]]. Ibuprofen: 200-400 mg every 4-6 hours [[CITE1]].",
    ),
    EvalQuery(
        query_id="q_dosing_table",
        text="Show the aspirin dosing table by age band.",
        category="tabular",
        relevant_chunk_ids=["c16"],
        expected_intent="tabular",
        expected_source_doc_ids=["doc-aspirin-dose-table"],
        expected_answer_facets=["12-15 years", "16+ years"],
        good_answer="12-15 years: 250-500 mg every 4-6 hours. 16+ years: 300-900 mg every 4-6 hours [[CITE0]].",
    ),
    EvalQuery(
        query_id="q_storage",
        text="How should aspirin be stored?",
        category="factual",
        relevant_chunk_ids=["c3", "c20"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-aspirin-pil", "doc-storage-extended"],
        expected_answer_facets=["25 degrees", "dry", "sunlight"],
        good_answer="Store below 25 degrees Celsius, in a dry place, away from sunlight [[CITE0]].",
        notes="c3 and c20 are near-duplicate content from two different source documents.",
    ),
    EvalQuery(
        query_id="q_max_daily_dose_conflict",
        text="What is the maximum daily dose of aspirin for adults?",
        category="conflicting",
        relevant_chunk_ids=["c17", "c18"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-conflicting-a", "doc-conflicting-b"],
        expected_answer_facets=["4000 mg", "3000 mg"],
        good_answer="Sources disagree: one states 4000 mg/day [[CITE0]], another states 3000 mg/day [[CITE1]].",
        notes="doc-conflicting-a says 4000mg, doc-conflicting-b says 3000mg for the SAME attribute (max daily dose). Real conflict.",
    ),
    EvalQuery(
        query_id="q_howto_procedure",
        text="Explain how to safely start a patient on aspirin therapy.",
        category="procedural",
        relevant_chunk_ids=["c1", "c7"],
        expected_intent="procedural",
        expected_source_doc_ids=["doc-aspirin-pil", "doc-bnf-aspirin"],
        expected_answer_facets=["325 mg", "peptic ulcer"],
        operation="explain",
        good_answer="Start at 325 mg every 4-6 hours [[CITE0]], using caution in patients with peptic ulcer history [[CITE1]].",
    ),
    EvalQuery(
        query_id="q_unanswerable_pregnancy",
        text="Is aspirin safe during the third trimester of pregnancy?",
        category="unanswerable",
        relevant_chunk_ids=[],
        expected_intent="factual",
        expected_source_doc_ids=[],
        expected_answer_facets=[],
        good_answer="",
        notes=(
            "No chunk in the corpus discusses aspirin+pregnancy (only ibuprofen+pregnancy, c13, "
            "which is a DIFFERENT drug and must not be used to answer this). Correct system "
            "behavior is no_answer=True; this tests whether retrieval false-fires on lexical "
            "overlap ('contraindicated', 'trimester', 'pregnancy') from the wrong drug's document."
        ),
    ),
    EvalQuery(
        query_id="q_side_effects",
        text="What are the common side effects of aspirin?",
        category="factual",
        relevant_chunk_ids=["c4"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-aspirin-pil"],
        expected_answer_facets=["stomach upset", "heartburn", "nausea"],
        good_answer="Common side effects include stomach upset, heartburn, and nausea [[CITE0]].",
    ),
    EvalQuery(
        query_id="q_ambiguous_dose",
        text="What's the dose?",
        category="ambiguous",
        relevant_chunk_ids=["c1", "c12", "c16"],
        expected_intent="factual",
        expected_source_doc_ids=[],
        expected_answer_facets=[],
        good_answer="",
        entity=None,
        operation="unsupported",
        notes=(
            "No entity specified (dose of WHAT? aspirin, ibuprofen, which formulation?) and the "
            "upstream parser could not classify the operation. Correct planner behavior is "
            "clarification_required=True (low intent confidence), not a confident silent guess."
        ),
    ),
    EvalQuery(
        query_id="q_duplicate_collision",
        text="What dose of aspirin should adults take for pain relief?",
        category="factual",
        relevant_chunk_ids=["c1", "c19"],
        expected_intent="factual",
        expected_source_doc_ids=["doc-aspirin-pil", "doc-aspirin-pil-duplicate"],
        expected_answer_facets=["325 mg", "every 4 to 6 hours"],
        good_answer="The adult dose is 325 mg every 4 to 6 hours [[CITE0]].",
        notes=(
            "c1 and c19 are near-duplicate text from two different source documents; both are "
            "legitimately relevant so both count in ground truth, but the evidence orchestrator's "
            "near-duplicate deduplication is expected to collapse them to one item in the pack."
        ),
    ),
    EvalQuery(
        query_id="q_navigational_section",
        text="Where is the interactions section for aspirin located?",
        category="navigational",
        relevant_chunk_ids=["c6", "c7"],
        expected_intent="navigational",
        expected_source_doc_ids=["doc-bnf-aspirin"],
        expected_answer_facets=["warfarin", "peptic ulcer"],
        good_answer="The interactions section covers warfarin [[CITE0]] and peptic ulcer precautions [[CITE1]].",
    ),
]

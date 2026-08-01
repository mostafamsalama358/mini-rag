from pathlib import Path

BASE = Path("src/fields/pharmacy/prompts/skills")
BASE.mkdir(parents=True, exist_ok=True)
PROMPTS = {
    "interactions": (
        "You answer drug INTERACTIONS from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "dosage": (
        "You answer DOSAGE from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "pregnancy": (
        "You answer PREGNANCY safety from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "lactation": (
        "You answer LACTATION questions from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "contraindications": (
        "List CONTRAINDICATIONS from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "warnings": (
        "Summarize WARNINGS from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "side_effects": (
        "List SIDE EFFECTS from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "storage": (
        "Answer STORAGE from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "leaflet": (
        "Leaflet-style summary from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "consultations": (
        "Counseling guidance from retrieved context only. Cite block IDs.\n"
        "Question: $query"
    ),
    "alternatives": (
        "Recommend in-corpus alternatives from retrieved evidence only. Cite block IDs.\n"
        "Question: $query"
    ),
}
for key, text in PROMPTS.items():
    (BASE / f"{key}.jinja").write_text(text, encoding="utf-8")

LEGAL = Path("src/fields/legal/prompts/skills")
LEGAL.mkdir(parents=True, exist_ok=True)
(LEGAL / "clause_lookup.jinja").write_text(
    "Answer from retrieved legal clauses only.\nQuestion: $query",
    encoding="utf-8",
)
(LEGAL / "obligations.jinja").write_text(
    "List obligations from retrieved context only.\nQuestion: $query",
    encoding="utf-8",
)
print("wrote", len(list(BASE.glob("*.jinja"))), "pharmacy skill prompts")

"""Generate pharmacy Skills Q&A markdown from live /answer API (project 2)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

API = "http://localhost:8000/api/v1/nlp/index/answer/2"
OUT = Path(__file__).resolve().parents[1] / "eval_run" / "pharmacy_skills_qa.md"
RESULTS_JSONL = Path(__file__).resolve().parents[1] / "eval_run" / "e2e_live_results" / "pharmacy_skills_qa.jsonl"

SKILL_DEFS: list[dict] = [
    {
        "id": "consultations",
        "name": "Consultations",
        "definition": (
            "استشارة صيدلية عامة حول دواء محدد: يجمع نقاطاً من الجرعة والتحذيرات "
            "وموانع الاستعمال والآثار الجانبية والحمل/الرضاعة حسب المتاح في الكوربس."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "نصيحة صيدلية عامة عن Congestal",
            "Give pharmacy counseling points for Brufen",
            "ما أهم نقاط الاستشارة لمريض يأخذ Glucophage؟",
            "Counsel a patient starting Augmentin",
            "نصائح عامة عند استخدام Panadol Extra",
            "What should a pharmacist tell a patient about Motilium?",
            "استشارة عن استخدام Daflon 500",
            "Counseling points for Lipitor",
            "نصيحة عامة عن Flagyl",
            "What counseling advice applies to Ventolin inhaler use?",
        ],
    },
    {
        "id": "interactions",
        "name": "Interactions",
        "definition": (
            "التحقق من وجود تفاعل دوائي بين دواءين مذكورين في السؤال، "
            "اعتماداً على مستندات التفاعلات في كوربس Excel."
        ),
        "needs": "اسمان لأدوية (زوج)",
        "questions": [
            "Does Congestal interact with Warfarin?",
            "هل في تفاعل بين Daflon و Warfarin؟",
            "Does Ciprobay interact with Warfarin?",
            "هل Augmentin يتفاعل مع Warfarin؟",
            "Does Flagyl interact with Warfarin?",
            "هل في تفاعل بين Congestal و Amitriptyline؟",
            "Does Panadol interact with Cholestyramine?",
            "هل Glucophage يتفاعل مع Vitamin B12؟",
            "Does Diflucan interact with Warfarin?",
            "هل في تفاعل بين Plavix و Aspirin؟",
        ],
    },
    {
        "id": "dosage",
        "name": "Dosage",
        "definition": (
            "الاستعلام عن الجرعة المعتادة للكبار/الأطفال والحد الأقصى اليومي "
            "حسب بيانات المنتج في الكوربس."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "What is the adult dose of Congestal?",
            "ما هي جرعة Brufen 400 للكبار؟",
            "What is the maximum daily dose of Panadol Extra?",
            "جرعة Glucophage للكبار؟",
            "What is the adult dose of Motilium?",
            "ما جرعة Augmentin 1g للبالغين؟",
            "Adult dose of Daflon 500?",
            "ما الجرعة القصوى اليومية لـ Congestal؟",
            "What is the adult dose of Flagyl 500?",
            "جرعة Strepsils للكبار؟",
        ],
    },
    {
        "id": "pregnancy",
        "name": "Pregnancy",
        "definition": (
            "معلومات أمان الدواء أثناء الحمل كما وردت في بيانات المنتج المفهرسة."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "Is Congestal safe in pregnancy?",
            "هل Brufen آمن في الحمل؟",
            "Is Flagyl safe during pregnancy?",
            "هل Glucophage آمن للحامل؟",
            "Is Daflon safe in pregnancy?",
            "هل Augmentin آمن أثناء الحمل؟",
            "Is Motilium safe in pregnancy?",
            "هل Panadol آمن في الحمل؟",
            "Is Lipitor safe during pregnancy?",
            "هل Diflucan آمن للحامل؟",
        ],
    },
    {
        "id": "lactation",
        "name": "Lactation",
        "definition": (
            "معلومات أمان الدواء أثناء الرضاعة الطبيعية من بيانات الكوربس."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "Is Congestal safe while breastfeeding?",
            "هل Brufen آمن أثناء الرضاعة؟",
            "Is Flagyl safe in lactation?",
            "هل Glucophage آمن مع الرضاعة؟",
            "Is Daflon safe while breastfeeding?",
            "هل Augmentin آمن للمرضعة؟",
            "Is Motilium safe in lactation?",
            "هل Panadol آمن أثناء الرضاعة؟",
            "Is Lipitor safe while breastfeeding?",
            "هل Diflucan آمن مع الرضاعة؟",
        ],
    },
    {
        "id": "contraindications",
        "name": "Contraindications",
        "definition": (
            "موانع الاستعمال: الحالات التي يُمنع فيها أخذ الدواء حسب النشرة/الكوربس."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "What are the contraindications of Congestal?",
            "ما موانع استخدام Brufen؟",
            "Contraindications of Flagyl?",
            "موانع Glucophage؟",
            "What are contraindications for Augmentin?",
            "موانع استخدام Motilium؟",
            "Contraindications of Lipitor?",
            "متى يُمنع Congestal؟",
            "What are contraindications of Diflucan?",
            "موانع استخدام Controloc؟",
        ],
    },
    {
        "id": "warnings",
        "name": "Warnings",
        "definition": (
            "التحذيرات والاحتياطات (بما فيها التحذيرات الجادة إن وُجدت) من بيانات المنتج."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "What are the warnings for Congestal?",
            "تحذيرات استخدام Panadol؟",
            "What warnings apply to Brufen?",
            "تحذيرات Flagyl؟",
            "Warnings for Glucophage?",
            "ما تحذيرات Augmentin؟",
            "What are the precautions for Motilium?",
            "تحذيرات Lipitor؟",
            "Warnings for Diflucan?",
            "ما الاحتياطات عند استخدام Congestal؟",
        ],
    },
    {
        "id": "side_effects",
        "name": "Side Effects",
        "definition": (
            "الآثار الجانبية المحتملة (رئيسية/ثانوية) كما وردت في الكوربس للمنتج."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "What are the side effects of Congestal?",
            "الآثار الجانبية لـ Brufen؟",
            "Side effects of Flagyl?",
            "أعراض جانبية Glucophage؟",
            "What are side effects of Augmentin?",
            "الآثار الجانبية لـ Motilium؟",
            "Side effects of Lipitor?",
            "أعراض جانبية لـ Panadol Extra؟",
            "What are the side effects of Diflucan?",
            "الآثار الجانبية لـ Daflon؟",
        ],
    },
    {
        "id": "storage",
        "name": "Storage",
        "definition": (
            "ظروف تخزين الدواء حسب تعليمات العبوة/البيانات المفهرسة."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "How should Congestal be stored?",
            "كيف أخزن Brufen؟",
            "Storage conditions for Flagyl?",
            "تخزين Glucophage؟",
            "How to store Augmentin?",
            "ظروف تخزين Motilium؟",
            "How should Lipitor be stored?",
            "تخزين Panadol؟",
            "Storage for Diflucan?",
            "كيف أخزن Ventolin inhaler؟",
        ],
    },
    {
        "id": "alternatives",
        "name": "Alternatives",
        "definition": (
            "توصية حسب الاحتياج/العَرَض (برد، صداع، سعال…) دون اشتراط اسم دواء؛ "
            "يبحث في دواعي الاستعمال ويقترح منتجات مناسبة من الكوربس."
        ),
        "needs": "وصف احتياج (العمر مفيد)",
        "questions": [
            "عندي برد وسني 25 سنة اخد ايه؟",
            "I have a headache, what can I take?",
            "عندي سعال منتج، آخد إيه؟",
            "I have a sore throat, age 30, what should I take?",
            "عندي احتقان أنف، نصيحة دوائية؟",
            "I have fever and body aches, what OTC options?",
            "عندي حموضة ومعدة، آخد إيه؟",
            "I have diarrhea, what can help from the catalog?",
            "عندي حساسية ورشح خفيف، اقتراحات؟",
            "Cold and flu symptoms for an adult — what products fit?",
        ],
    },
    {
        "id": "leaflet",
        "name": "Leaflet",
        "definition": (
            "معلومات عامة عن المنتج من الكوربس (استخدامات، نظرة شاملة) بدون تقييد حقل واحد؛ "
            "يشترط اسم دواء. الاسم التاريخي Leaflet مع أن المصدر الحي هو Excel workbook."
        ),
        "needs": "اسم دواء واحد",
        "questions": [
            "What is Congestal and what is it used for?",
            "إيه هو Brufen وإيه استخداماته؟",
            "What is Glucophage used for?",
            "عرف لي Augmentin باختصار",
            "What is Daflon 500?",
            "إيه استخدامات Flagyl؟",
            "What is Motilium?",
            "لخص معلومات Lipitor",
            "What is Diflucan used for?",
            "إيه هو Congestal باختصار؟",
        ],
    },
]


def ask(skill_id: str, text: str, timeout: int = 240) -> dict:
    r = requests.post(
        API,
        json={"text": text, "skill_id": skill_id, "limit": 8},
        timeout=timeout,
    )
    try:
        payload = r.json()
    except Exception:
        payload = {"raw": r.text[:2000]}
    return {
        "http_status": r.status_code,
        "answer": payload.get("answer") or payload.get("clarification") or "",
        "needs_clarification": bool(payload.get("needs_clarification")),
        "signal": payload.get("signal"),
        "payload": payload,
    }


def load_done() -> set[tuple[str, str]]:
    done: set[tuple[str, str]] = set()
    if RESULTS_JSONL.exists():
        for line in RESULTS_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                done.add((row["skill_id"], row["question"]))
            except Exception:
                continue
    return done


def main() -> None:
    RESULTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    done = load_done()
    # Rebuild markdown from jsonl + defs at the end; stream answers into jsonl.
    total = sum(len(s["questions"]) for s in SKILL_DEFS)
    remaining = total - len(done)
    print(f"resume: {len(done)} done, {remaining} remaining", flush=True)

    with RESULTS_JSONL.open("a", encoding="utf-8") as jf:
        n = len(done)
        for skill in SKILL_DEFS:
            sid = skill["id"]
            for q in skill["questions"]:
                if (sid, q) in done:
                    continue
                n += 1
                print(f"[{n}/{total}] {sid}", flush=True)
                try:
                    res = ask(sid, q)
                except Exception as exc:
                    res = {
                        "http_status": 0,
                        "answer": f"[ERROR] {type(exc).__name__}: {exc}",
                        "needs_clarification": False,
                        "signal": "error",
                    }
                jf.write(
                    json.dumps(
                        {
                            "skill_id": sid,
                            "question": q,
                            "http_status": res.get("http_status"),
                            "answer": res.get("answer"),
                            "needs_clarification": res.get("needs_clarification"),
                            "signal": res.get("signal"),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                jf.flush()
                time.sleep(0.3)

    write_markdown_from_jsonl()
    print(f"DONE -> {OUT}", flush=True)


def write_markdown_from_jsonl() -> None:
    by_key: dict[tuple[str, str], dict] = {}
    if RESULTS_JSONL.exists():
        for line in RESULTS_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            by_key[(row["skill_id"], row["question"])] = row

    lines: list[str] = []
    lines.append("# Pharmacy Skills — أسئلة وإجابات مرجعية")
    lines.append("")
    lines.append(
        "ملف مرجعي لكل Skill في مجال الصيدلة: التعريف، متطلبات الإدخال، "
        "ثم 10 أسئلة مع إجابات حية من `/api/v1/nlp/index/answer/2` على كوربس "
        "`RAG_CORPUS` (Excel workbook) — project_id=2."
    )
    lines.append("")
    lines.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## فهرس المهارات")
    lines.append("")
    for i, skill in enumerate(SKILL_DEFS, 1):
        lines.append(
            f"{i}. **{skill['name']}** (`{skill['id']}`) — {skill['definition']}"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    for skill in SKILL_DEFS:
        sid = skill["id"]
        lines.append(f"## {skill['name']} (`{sid}`)")
        lines.append("")
        lines.append(f"**التعريف:** {skill['definition']}")
        lines.append("")
        lines.append(f"**المطلوب من المستخدم:** {skill['needs']}")
        lines.append("")
        for qi, q in enumerate(skill["questions"], 1):
            row = by_key.get((sid, q))
            ans = ((row or {}).get("answer") or "").strip() or "_(no answer yet)_"
            flag = (
                " *(clarification)*"
                if (row or {}).get("needs_clarification")
                else ""
            )
            lines.append(f"### س{qi}. {q}")
            lines.append("")
            lines.append(f"**الإجابة{flag}:**")
            lines.append("")
            lines.append(ans)
            lines.append("")
        lines.append("---")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

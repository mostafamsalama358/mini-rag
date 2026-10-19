"""Probe all four Madrsty subjects against /answer (project 5)."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "http://localhost:8000/api/v1/nlp/index/answer/5"
HEADERS = {
    "X-User-Id": "user123",
    "Content-Type": "application/json; charset=utf-8",
}
GAP_S = 35.0
QUOTA_WAIT_S = 90.0
LIMIT = 12

MISS_MARKERS = (
    "لم أجد",
    "غير متوفر",
    "غير موجودة",
    "لا يمكنني",
    "لم يتم",
    "لم يذكر",
    "المعلومات المطلوبة غير",
    "could not find",
    "no indexed",
    "quota",
    "دواء",
)

CASES: list[tuple[str, str, str]] = [
    # Psychology
    ("P01", "psychology_summary", "عرّف علم النفس حسب الكتاب."),
    ("P02", "psychology_explain", "ما الميادين النظرية والتطبيقية لعلم النفس؟"),
    ("P03", "psychology_exercise", "من يستفيد من دراسة علم النفس؟ اذكر الفئات في الكتاب."),
    ("P04", "psychology_explain", "ما علاقة وظائف أعضاء الجسم بالسلوك؟"),
    ("P05", "psychology_explain", "ما الجهاز العصبي حسب الكتاب؟"),
    ("P06", "psychology_explain", "ما الغدد الصماء وما أثرها في السلوك؟"),
    ("P07", "psychology_exercise", "ماذا يحدث عند نقص إفرازات الغدة الدرقية وزيادة إفراز الغدة النخامية؟"),
    ("P08", "psychology_explain", "عرّف الدافعية / دوافع السلوك."),
    ("P09", "psychology_explain", "ما الانفعال وما مكوناته؟"),
    ("P10", "psychology_explain", "ما الانفعالات الأساسية والمركبة؟ وما وظيفة الخوف؟"),
    ("P11", "psychology_explain", "ما العمليات العقلية التي يدرسها الفصل الخامس؟"),
    ("P12", "psychology_example", "هات مثالًا على التعلم بالاشتراط من نشاط الكتاب."),
    ("P13", "psychology_explain", "عرّف النسيان حسب الكتاب."),
    ("P14", "psychology_explain", "ما الإدراك الحسي وما العوامل المؤثرة فيه؟"),
    ("P15", "psychology_explain", "ما أنواع التفكير؟ وما التفكير المبدع؟"),
    ("P16", "psychology_explain", "ما قوانين النمو النفسي العامة؟"),
    ("P17", "psychology_explain", "ما التوافق النفسي والاجتماعي وما أساليبه؟"),
    ("P18", "psychology_explain", "من روّاد نشأة علم الاجتماع في الكتاب؟ وكيف عرّف أوجست كونت علم الاجتماع؟"),
    ("P19", "psychology_explain", "ما فروع علم الاجتماع المذكورة؟"),
    ("P20", "psychology_explain", "قارن الأسرة النووية والأسرة الممتدة، ثم ما التغير الاجتماعي وعوامله؟ وما أمثلة المشكلات الاجتماعية؟"),
    # Statistics
    ("S01", "statistics_summary", "ما اسم الكتاب والمرحلة؟"),
    ("S02", "statistics_explain", "ماذا يدرس درس Real Numbers؟"),
    ("S03", "statistics_explain", "ما موضوع Roots and Radical Expressions؟"),
    ("S04", "statistics_example", "هات مثالًا من الكتاب على تبسيط تعبير جذري (Simplifying Radical Expressions)."),
    ("S05", "statistics_explain", "كيف نجمع ونطرح التعبيرات الجذرية؟"),
    ("S06", "statistics_explain", "كيف نضرب ونقسم التعبيرات الجذرية؟"),
    ("S07", "statistics_formula", "ما المقصود بالمرافق Conjugate وكيف يُستخدم؟"),
    ("S08", "statistics_explain", "اشرح الأسس النسبية Rational Exponents وخصائصها."),
    ("S09", "statistics_explain", "ما الفرق بين Qualitative Data و Quantitative Data؟"),
    ("S10", "statistics_explain", "ما أنواع وطرق جمع البيانات Types and methods of Data Collection؟"),
    ("S11", "statistics_explain", "عدّد Methods of Data Collecting حسب الكتاب."),
    ("S12", "statistics_explain", "ما أنواع العيّنات Samples Types في الكتاب؟"),
    ("S13", "statistics_explain", "ما العينة العشوائية البسيطة Simple Random Sample؟"),
    ("S14", "statistics_explain", "ما العينة الطبقية Stratified Random Sample؟"),
    ("S15", "statistics_explain", "ما العينة المنتظمة Systematic Random Sample؟"),
    ("S16", "statistics_explain", "ما طرق عرض البيانات Ways to Display Data؟"),
    ("S17", "statistics_example", "اشرح Frequency Table ومتى تُستخدم."),
    ("S18", "statistics_explain", "متى نستخدم Pie Chart ومتى Histogram؟"),
    ("S19", "statistics_explain", "ما Frequency Curve و Frequency Polygon؟"),
    ("S20", "statistics_exercise", "الكتاب يشرح تمثيل البيانات على Excel (Histogram / Data Analysis). ماذا يطلب من الطالب؟"),
    # Geography
    ("G01", "geography_summary", "ما اسم الكتاب والمرحلة والجهة الناشرة؟"),
    ("G02", "geography_explain", "ما موضوعات الباب الأول في الكتاب؟"),
    ("G03", "geography_explain", "ما فصول الباب الثاني «كوكب الأرض»؟"),
    ("G04", "geography_explain", "ماذا يدرس فصل الإنسان والكون؟"),
    ("G05", "geography_explain", "ما موضوعات فصل المجموعة الشمسية؟"),
    ("G06", "geography_explain", "عدّد الخصائص العامة للكرة الأرضية حسب الكتاب."),
    ("G07", "geography_explain", "ما أقسام صخور القشرة الأرضية؟"),
    ("G08", "geography_explain", "ما أغلفة الأرض التي يدرسها الباب الثالث؟"),
    ("G09", "geography_explain", "ما عناصر الطقس والمناخ في فصل الغلاف الجوي؟"),
    ("G10", "geography_explain", "ما أنواع أقاليم الغابات في الفهرس؟"),
    ("G11", "geography_explain", "ما نتائج دوران الأرض حول نفسها (الدورة المحورية)؟"),
    ("G12", "geography_explain", "ماذا يذكر الكتاب عن أوجه القمر والمد والجزر والكسوف؟"),
    ("G13", "geography_explain", "تكلم عن الزلازل في الكتاب: تحت أي قوى تصنَّف؟"),
    ("G14", "geography_explain", "ما أجزاء مخروط البركان حسب الكتاب؟"),
    ("G15", "geography_explain", "ما أنواع الانكسارات المذكورة؟"),
    ("G16", "geography_map", "ما عناصر الخريطة الأساسية في الكتاب؟"),
    ("G17", "geography_map", "ما أنواع الخرائط المذكورة في الكتاب؟"),
    ("G18", "geography_exercise", "في تمارين الكتاب: ارسم خريطة توضح ماذا عن البحار والمحيطات؟"),
    ("G19", "geography_exercise", "التمرين يطلب جدولاً عن الغلاف الجوي يوضح ماذا؟"),
    ("G20", "geography_example", "هات مثالاً من الكتاب على الشبكة الجغرافية أو دوائر العرض."),
    # French (4th subject — from madrsty_skills_qa.md)
    ("F01", "french_vocabulary", "ما التعبيرات الفرنسية لحالة الطقس في درس Il fait un temps superbe؟"),
    ("F02", "french_grammar", "حسب درس الجنسيات: كيف نقول صفة الجنسية للكويت وفرنسا ومصر؟ وما اسم البلد؟"),
    ("F03", "french_grammar", "اشرح تكوين passé composé: متى avoir ومتى être؟ أعطِ أمثلة من الكتاب."),
    ("F04", "french_dialogue", "لخّص حوار الـ tchatche بين Hassan و Jean-Pierre. من هو Jules Verne؟"),
    ("F05", "french_vocabulary", "ماذا تعني Une tchatche؟ وما أضداد Bonjour و Un peu؟"),
    ("F06", "french_dialogue", "ماذا يقول الأستاذ في الصف في درس Premier contact؟"),
    ("F07", "french_exercise", "كيف نسأل ونقول وسيلة النقل للذهاب إلى المدرسة حسب تمرين Communication؟"),
    ("F08", "french_culture", "أين يفضّل الطلاب الأجانب السكن حسب فقرة Culture؟ وما أنواع المساكن المذكورة؟"),
]


def looks_like_miss(answer: str) -> bool:
    text = (answer or "").strip().casefold()
    if not text:
        return True
    return any(marker.casefold() in text for marker in MISS_MARKERS)


def ask(skill_id: str, text: str) -> dict:
    payload = json.dumps(
        {"text": text, "skill_id": skill_id, "limit": LIMIT},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(URL, data=payload, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "http": resp.status,
                "signal": body.get("signal"),
                "answer": body.get("answer") or body.get("message") or "",
                "needs_clarification": body.get("needs_clarification"),
            }
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw": raw}
        return {
            "http": exc.code,
            "signal": body.get("signal"),
            "answer": body.get("answer") or body.get("message") or raw[:500],
            "needs_clarification": body.get("needs_clarification"),
        }


def _save(dest: Path, by_id: dict[str, dict]) -> None:
    ordered = [by_id[qid] for qid, _, _ in CASES if qid in by_id]
    dest.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    dest = Path(__file__).with_name("probe_madrsty_four_subjects.json")
    by_id: dict[str, dict] = {}
    if dest.exists():
        for row in json.loads(dest.read_text(encoding="utf-8")):
            qid = row.get("id")
            if qid:
                by_id[qid] = row

    pending = [
        (qid, skill, text)
        for qid, skill, text in CASES
        if by_id.get(qid, {}).get("http") != 200
    ]
    print(f"resume pending={len(pending)} kept={len(by_id) - len(pending)} gap={GAP_S}s", flush=True)

    for i, (qid, skill, text) in enumerate(pending, start=1):
        t0 = time.time()
        row = ask(skill, text)
        if row.get("http") == 503:
            print(f"{i:02d}/{len(pending)} {qid} quota — wait {int(QUOTA_WAIT_S)}s then retry", flush=True)
            time.sleep(QUOTA_WAIT_S)
            t0 = time.time()
            row = ask(skill, text)
        row.update(
            {
                "id": qid,
                "skill_id": skill,
                "question": text,
                "elapsed_s": round(time.time() - t0, 1),
                "looks_like_miss": looks_like_miss(row.get("answer") or ""),
            }
        )
        by_id[qid] = row
        _save(dest, by_id)
        preview = (row.get("answer") or "").replace("\n", " ")[:140]
        flag = "MISS" if row["looks_like_miss"] else "ok"
        print(
            f"{i:02d}/{len(pending)} {qid} {flag} http={row.get('http')} "
            f"sig={row.get('signal')} {row['elapsed_s']}s | {preview}",
            flush=True,
        )
        if i < len(pending):
            time.sleep(GAP_S)
    print("WROTE", dest)


if __name__ == "__main__":
    main()

"""Probe Statistics + Psychology skills against /answer (project 5)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

URL = "http://localhost:8000/api/v1/nlp/index/answer/5"
HEADERS = {
    "X-User-Id": "user123",
    "Content-Type": "application/json",
}

CASES = [
    # Statistics
    ("S01", "statistics_summary", "ما اسم الكتاب والمرحلة والجهة الناشرة؟"),
    ("S02", "statistics_explain", "ماذا يدرس درس Real Numbers في الكتاب؟"),
    ("S03", "statistics_explain", "ما موضوع Roots and Radical Expressions؟"),
    ("S04", "statistics_example", "هات مثالا من الكتاب على تبسيط تعبير جذري Simplifying Radical Expressions."),
    ("S05", "statistics_explain", "كيف نجمع ونطرح التعبيرات الجذرية Addition and Subtraction of Radical Expressions؟"),
    ("S06", "statistics_explain", "كيف نضرب ونقسم التعبيرات الجذرية Multiplication and Division of Radical Expressions؟"),
    ("S07", "statistics_formula", "ما المقصود بالمرافق Conjugate وكيف يستخدم؟"),
    ("S08", "statistics_explain", "اشرح الاسس النسبية Rational Exponents وخصائصها."),
    ("S09", "statistics_explain", "ما الفرق بين Qualitative Data و Quantitative Data؟"),
    ("S10", "statistics_explain", "ما انواع وطرق جمع البيانات Types and methods of Data Collection؟"),
    ("S11", "statistics_explain", "عدد Methods of Data Collecting حسب الكتاب."),
    ("S12", "statistics_explain", "ما انواع العينات Samples Types في الكتاب؟"),
    ("S13", "statistics_explain", "ما العينة العشوائية البسيطة Simple Random Sample؟"),
    ("S14", "statistics_explain", "ما العينة الطبقية Stratified Random Sample؟"),
    ("S15", "statistics_explain", "ما العينة المنتظمة Systematic Random Sample؟"),
    ("S16", "statistics_explain", "ما طرق عرض البيانات Ways to Display Data؟"),
    ("S17", "statistics_example", "اشرح Frequency Table ومتى تستخدم."),
    ("S18", "statistics_explain", "متى نستخدم Pie Chart ومتى Histogram؟"),
    ("S19", "statistics_explain", "ما Frequency Curve و Frequency Polygon؟"),
    ("S20", "statistics_exercise", "الكتاب يشرح تمثيل البيانات على Excel Histogram Data Analysis. ماذا يطلب من الطالب؟"),
    ("Sneg", "statistics_explain", "ما اقسام صخور القشرة الارضية؟"),
    # Psychology & Sociology
    ("P01", "psychology_summary", "عرف علم النفس حسب الكتاب."),
    ("P02", "psychology_explain", "ما الميادين النظرية والتطبيقية لعلم النفس؟"),
    ("P03", "psychology_exercise", "من يستفيد من دراسة علم النفس؟ اذكر الفئات في الكتاب."),
    ("P04", "psychology_explain", "ما علاقة وظائف اعضاء الجسم بالسلوك؟"),
    ("P05", "psychology_explain", "ما الجهاز العصبي حسب الكتاب؟"),
    ("P06", "psychology_explain", "ما الغدد الصماء وما اثرها في السلوك؟"),
    ("P07", "psychology_exercise", "ماذا يحدث عند نقص افرازات الغدة الدرقية وزيادة افراز الغدة النخامية؟"),
    ("P08", "psychology_explain", "عرف الدافعية ودوافع السلوك."),
    ("P09", "psychology_explain", "ما الانفعال وما مكوناته؟"),
    ("P10", "psychology_explain", "ما الانفعالات الاساسية والمركبة؟ وما وظيفة الخوف؟"),
    ("P11", "psychology_explain", "ما العمليات العقلية التي يدرسها الفصل الخامس؟"),
    ("P12", "psychology_example", "هات مثالا على التعلم بالاشتراط من نشاط الكتاب."),
    ("P13", "psychology_explain", "عرف النسيان حسب الكتاب."),
    ("P14", "psychology_explain", "ما الادراك الحسي وما العوامل المؤثرة فيه؟"),
    ("P15", "psychology_explain", "ما انواع التفكير؟ وما التفكير المبدع؟"),
    ("P16", "psychology_explain", "ما قوانين النمو النفسي العامة؟"),
    ("P17", "psychology_explain", "ما التوافق النفسي والاجتماعي وما اساليبه؟"),
    ("P18", "psychology_explain", "من رواد نشاة علم الاجتماع في الكتاب؟ وكيف عرف اوجست كونت علم الاجتماع؟"),
    ("P19", "psychology_explain", "ما فروع علم الاجتماع المذكورة في الكتاب؟"),
    ("P20", "psychology_explain", "قارن الاسرة النووية والاسرة الممتدة، ثم ما التغير الاجتماعي وعوامله؟ وما امثلة المشكلات الاجتماعية؟"),
    ("Pneg", "psychology_explain", "ما العينة الطبقية Stratified Random Sample؟"),
]


def ask(skill_id: str, text: str) -> dict:
    payload = json.dumps({"text": text, "skill_id": skill_id, "limit": 6}).encode("utf-8")
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


def main() -> None:
    out = []
    for i, (qid, skill, text) in enumerate(CASES, start=1):
        t0 = time.time()
        row = ask(skill, text)
        row.update(
            {
                "id": qid,
                "skill_id": skill,
                "question": text,
                "elapsed_s": round(time.time() - t0, 1),
            }
        )
        out.append(row)
        preview = (row.get("answer") or "").replace("\n", " ")[:160]
        print(f"{i:02d}/{len(CASES)} {qid} http={row.get('http')} sig={row.get('signal')} {row['elapsed_s']}s | {preview}", flush=True)

    dest = Path(__file__).with_name("probe_madrsty_new_subjects.json")
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", dest)


if __name__ == "__main__":
    main()

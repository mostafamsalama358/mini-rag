"""Run the G8a/G9a science test questions against /answer (project 5).

Usage:
    python eval_run/probe_madrsty_science.py              # run all pending cases
    python eval_run/probe_madrsty_science.py --grade G8a  # one class only
    python eval_run/probe_madrsty_science.py --markdown   # regenerate the .md sheet only
"""
from __future__ import annotations

import argparse
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

HERE = Path(__file__).parent
CASES_PATH = HERE / "science_test_questions.json"
RESULTS_PATH = HERE / "probe_madrsty_science.json"
MARKDOWN_PATH = HERE / "science_test_questions.md"

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
)

GRADE_TITLES = {"G8a": "الصف الثامن (G8a)", "G9a": "الصف التاسع (G9a)"}


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def write_markdown(cases: list[dict]) -> None:
    lines = [
        "# أسئلة اختبار العلوم — مدرستي",
        "",
        "في الشات: اختر الفصل، ثم **العلوم**، ثم نوع السؤال (skill) المكتوب مع كل سؤال.",
        "أرقام الصفحات هي أرقام صفحات ملف الـ PDF.",
        "",
    ]
    for grade in ("G8a", "G9a"):
        lines += [f"## {GRADE_TITLES[grade]}", ""]
        for case in (c for c in cases if c["grade"] == grade):
            lines += [
                f"### {case['id']} — `{case['skill_id']}` — ص {case['pages']}",
                "",
                f"**السؤال:** {case['question']}",
                "",
                f"**الإجابة المتوقعة:** {case['expected_answer']}",
                "",
                f"**كلمات مفتاحية للتصحيح:** {'، '.join(case['key_points'])}",
                "",
            ]
    MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")
    print("WROTE", MARKDOWN_PATH)


def looks_like_miss(answer: str) -> bool:
    text = (answer or "").strip().casefold()
    if not text:
        return True
    return any(marker.casefold() in text for marker in MISS_MARKERS)


def key_point_hits(answer: str, key_points: list[str]) -> list[str]:
    text = (answer or "").casefold()
    return [kp for kp in key_points if kp.casefold() in text]


def ask(case: dict) -> dict:
    payload = json.dumps(
        {
            "text": case["question"],
            "skill_id": case["skill_id"],
            "limit": LIMIT,
            "metadata_filter": {"grade": case["grade"]},
        },
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
        }


def _save(cases: list[dict], by_id: dict[str, dict]) -> None:
    ordered = [by_id[c["id"]] for c in cases if c["id"] in by_id]
    RESULTS_PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cases: list[dict], grade: str | None) -> None:
    by_id: dict[str, dict] = {}
    if RESULTS_PATH.exists():
        for row in json.loads(RESULTS_PATH.read_text(encoding="utf-8")):
            if row.get("id"):
                by_id[row["id"]] = row

    pending = [
        c for c in cases
        if (grade is None or c["grade"] == grade) and by_id.get(c["id"], {}).get("http") != 200
    ]
    print(f"pending={len(pending)} gap={GAP_S}s", flush=True)

    for i, case in enumerate(pending, start=1):
        t0 = time.time()
        row = ask(case)
        if row.get("http") == 503:
            print(f"{i:02d}/{len(pending)} {case['id']} quota — wait {int(QUOTA_WAIT_S)}s", flush=True)
            time.sleep(QUOTA_WAIT_S)
            t0 = time.time()
            row = ask(case)
        hits = key_point_hits(row.get("answer") or "", case["key_points"])
        row.update(
            {
                "id": case["id"],
                "grade": case["grade"],
                "skill_id": case["skill_id"],
                "question": case["question"],
                "expected_answer": case["expected_answer"],
                "elapsed_s": round(time.time() - t0, 1),
                "looks_like_miss": looks_like_miss(row.get("answer") or ""),
                "key_points_hit": hits,
                "key_point_score": round(len(hits) / len(case["key_points"]), 2),
            }
        )
        by_id[case["id"]] = row
        _save(cases, by_id)
        flag = "MISS" if row["looks_like_miss"] else "ok"
        preview = (row.get("answer") or "").replace("\n", " ")[:120]
        print(
            f"{i:02d}/{len(pending)} {case['id']} {flag} http={row.get('http')} "
            f"kp={len(hits)}/{len(case['key_points'])} {row['elapsed_s']}s | {preview}",
            flush=True,
        )
        if i < len(pending):
            time.sleep(GAP_S)

    done = [by_id[c["id"]] for c in cases if c["id"] in by_id]
    if done:
        avg = sum(r.get("key_point_score", 0) for r in done) / len(done)
        misses = sum(1 for r in done if r.get("looks_like_miss"))
        print(f"SUMMARY answered={len(done)} misses={misses} avg_key_point_score={avg:.2f}")
    print("WROTE", RESULTS_PATH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", choices=sorted(GRADE_TITLES))
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()

    cases = load_cases()
    write_markdown(cases)
    if not args.markdown:
        run(cases, args.grade)


if __name__ == "__main__":
    main()

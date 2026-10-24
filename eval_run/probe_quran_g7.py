"""Run the G7 Quran chat questions against /answer (project 5).

Usage:
    python eval_run/probe_quran_g7.py
    python eval_run/probe_quran_g7.py --ids Q01,Q08
    python eval_run/probe_quran_g7.py --grade G7a
    python eval_run/probe_quran_g7.py --redo
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import urllib.error
import urllib.request
from pathlib import Path

URL = "http://localhost:8000/api/v1/nlp/index/answer/5"
HEADERS = {
    "X-User-Id": "user123",
    "Content-Type": "application/json; charset=utf-8",
}
LIMIT = 12
QUOTA_WAIT_S = 90.0

HERE = Path(__file__).parent
CASES_PATH = HERE / "quran_g7_questions.json"
RESULTS_PATH = HERE / "probe_quran_g7.json"
REPORT_PATH = HERE / "probe_quran_g7.md"

MISS_MARKERS = (
    "لم أجد",
    "غير متوفر",
    "غير موجودة",
    "لا يمكنني",
    "لم يتم",
    "لم يذكر",
    "لا تتوفر",
    "المعلومات المطلوبة غير",
    "could not find",
    "no indexed",
    "quota",
)


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def service_key() -> str:
    configured = (os.environ.get("MINIRAG_SERVICE_API_KEY") or "").strip()
    if configured:
        return configured
    env_path = HERE.parent / "docker" / "env" / ".env.app"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("MINIRAG_SERVICE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def looks_like_miss(answer: str, signal: str | None, http: int | None = 200) -> bool:
    if http != 200:
        return True
    if signal in {"rag_no_context", "rag_answer_error", "rag_clarification_needed"}:
        return True
    text = (answer or "").strip().casefold()
    if not text:
        return True
    return any(marker.casefold() in text for marker in MISS_MARKERS)


def key_point_hits(answer: str, key_points: list[str]) -> list[str]:
    text = (answer or "").casefold()
    return [kp for kp in key_points if kp.casefold() in text]


def ask(case: dict, grade: str) -> dict:
    payload = json.dumps(
        {
            "text": case["question"],
            "skill_id": case["skill_id"],
            "limit": LIMIT,
            "metadata_filter": {"grade": grade},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    headers = dict(HEADERS)
    key = service_key()
    if key:
        headers["X-Service-Key"] = key
    req = urllib.request.Request(URL, data=payload, headers=headers, method="POST")
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
            "answer": body.get("answer") or body.get("detail") or body.get("message") or raw[:800],
        }
    except urllib.error.URLError as exc:
        return {"http": 0, "signal": None, "answer": str(exc.reason)}


def _save(cases: list[dict], by_id: dict[str, dict]) -> None:
    ordered = [by_id[c["id"]] for c in cases if c["id"] in by_id]
    RESULTS_PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(ordered)


def write_report(rows: list[dict]) -> None:
    misses = [r for r in rows if r.get("looks_like_miss")]
    lines = [
        "# قرآن الصف السابع — نتائج الشات",
        "",
        f"الإجابات: {len(rows)} | بدون إجابة مفيدة: {len(misses)}",
        "",
        "| id | skill | signal | نقاط | الحالة |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        state = "فاضية" if row.get("looks_like_miss") else "فيها إجابة"
        score = row.get("key_point_score")
        lines.append(
            f"| {row.get('id')} | `{row.get('skill_id')}` | {row.get('signal')} | {score} | {state} |"
        )
    lines += ["", "## الإجابات", ""]
    for row in rows:
        lines += [
            f"### {row.get('id')} — `{row.get('skill_id')}` — {row.get('signal')}",
            "",
            f"**السؤال:** {row.get('question')}",
            "",
            f"**المتوقع:** {row.get('expected_answer')}",
            "",
            row.get("answer") or "(لا إجابة)",
            "",
        ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run(cases: list[dict], grade: str, ids: set[str] | None, gap: float, redo: bool) -> None:
    by_id: dict[str, dict] = {}
    if RESULTS_PATH.exists() and not redo:
        for row in json.loads(RESULTS_PATH.read_text(encoding="utf-8")):
            if row.get("id"):
                by_id[row["id"]] = row

    pending = []
    for case in cases:
        if ids is not None and case["id"] not in ids:
            continue
        previous = by_id.get(case["id"])
        if previous and previous.get("http") == 200 and not redo:
            continue
        pending.append(case)

    print(f"pending={len(pending)} grade={grade} gap={gap}s", flush=True)
    for i, case in enumerate(pending, start=1):
        t0 = time.time()
        row = ask(case, grade)
        if row.get("http") == 503:
            print(f"{i:02d}/{len(pending)} {case['id']} quota — wait {int(QUOTA_WAIT_S)}s", flush=True)
            time.sleep(QUOTA_WAIT_S)
            t0 = time.time()
            row = ask(case, grade)
        hits = key_point_hits(row.get("answer") or "", case["key_points"])
        row.update(
            {
                "id": case["id"],
                "grade": grade,
                "skill_id": case["skill_id"],
                "question": case["question"],
                "expected_answer": case["expected_answer"],
                "pages": case["pages"],
                "elapsed_s": round(time.time() - t0, 1),
                "looks_like_miss": looks_like_miss(
                    row.get("answer") or "", row.get("signal"), row.get("http")
                ),
                "key_points_hit": hits,
                "key_point_score": round(len(hits) / len(case["key_points"]), 2) if case["key_points"] else 0,
            }
        )
        by_id[case["id"]] = row
        _save(cases, by_id)
        flag = "MISS" if row["looks_like_miss"] else "ok"
        preview = (row.get("answer") or "").replace("\n", " ")[:140]
        print(
            f"{i:02d}/{len(pending)} {case['id']} {flag} http={row.get('http')} "
            f"signal={row.get('signal')} kp={len(hits)}/{len(case['key_points'])} "
            f"{row['elapsed_s']}s | {preview}",
            flush=True,
        )
        if i < len(pending) and gap > 0:
            time.sleep(gap)

    done = [by_id[c["id"]] for c in cases if c["id"] in by_id and (ids is None or c["id"] in ids)]
    if done:
        misses = sum(1 for r in done if r.get("looks_like_miss"))
        print(f"SUMMARY answered={len(done)} misses={misses}")
    print("WROTE", RESULTS_PATH)
    print("WROTE", REPORT_PATH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade", default="G7")
    parser.add_argument("--ids", default="")
    parser.add_argument("--gap", type=float, default=2.0)
    parser.add_argument("--redo", action="store_true")
    args = parser.parse_args()
    ids = {item.strip() for item in args.ids.split(",") if item.strip()} or None
    run(load_cases(), args.grade, ids, args.gap, args.redo)


if __name__ == "__main__":
    main()

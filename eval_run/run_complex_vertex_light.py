"""Vertex-light evaluation: SQL coverage + optional search/answer.

Avoids generation when possible. With RAG_SEMANTIC_PARSER_ENABLED=false,
answer still needs Vertex for the final LLM call.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import requests

API = "http://localhost:8000"
OUT = Path(__file__).resolve().parents[1] / "e2e_live_results" / "complex_vertex_light.json"

QUESTIONS = [
    {
        "id": "Q1_stack_ar",
        "q": "مريض بياخد Panadol Advance 500 مرتين، وخد Flurest-N وCongestal. هل فيه خطر؟",
        "expect_entities": ["Panadol", "Flurest-N", "Congestal"],
        "expect_neg": False,
    },
    {
        "id": "Q2_stack_en",
        "q": "Can a patient take Panadol Cold & Flu Day together with Adol 500 and Comtrex?",
        "expect_entities": ["Panadol", "Adol", "Comtrex"],
        "expect_neg": False,
    },
    {
        "id": "Q3_twins",
        "q": "Are Augmentin 1 g and Hi-Biotic 1 g the same active combination?",
        "expect_entities": ["Augmentin", "Hi-Biotic"],
        "expect_neg": False,
    },
    {
        "id": "Q4_plavix_ppi",
        "q": "Patient on Plavix 75 + Aspocid. Reflux — Risek 20 or Controloc 20?",
        "expect_entities": ["Plavix", "Aspocid", "Risek", "Controloc"],
        "expect_neg": False,
    },
    {
        "id": "Q5_anaseziago",
        "q": "Is Anaseziago the same as thiocolchicoside muscle relaxant?",
        "expect_entities": ["Anaseziago"],
        "expect_neg": False,
    },
    {
        "id": "Q6_lipitor_preg",
        "q": "Is Lipitor safe in pregnancy?",
        "expect_entities": ["Lipitor"],
        "expect_neg": False,
    },
    {
        "id": "Q7_acid",
        "q": "Jeparilon vs Controloc vs Risek vs Gaviscon classify each",
        "expect_entities": ["Jeparilon", "Controloc", "Risek", "Gaviscon"],
        "expect_neg": False,
    },
    {
        "id": "Q8_cipro_iron",
        "q": "Ciprobay with Ferrotron and Gaviscon timing",
        "expect_entities": ["Ciprobay", "Ferrotron", "Gaviscon"],
        "expect_neg": False,
    },
    {
        "id": "Q9_daflon",
        "q": "Daflon 500 vs Daflon 1000 usual daily tablet counts",
        "expect_entities": ["Daflon"],
        "expect_neg": False,
    },
    {
        "id": "Q10_vancomycin_neg",
        "q": "What is the vancomycin meningitis dose for a 70 kg adult?",
        "expect_entities": ["vancomycin"],
        "expect_neg": True,
    },
]


def psql(sql: str) -> str:
    return subprocess.check_output(
        [
            "docker",
            "exec",
            "pgvector",
            "psql",
            "-U",
            "postgres",
            "-d",
            "algorag",
            "-t",
            "-A",
            "-c",
            sql,
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def entity_count(name: str) -> int:
    safe = name.replace("'", "''")
    return int(
        psql(
            "SELECT COUNT(*) FROM collection_768_2 WHERE "
            f"metadata->>'entity' ILIKE '%{safe}%' OR text ILIKE '%{safe}%';"
        ).strip()
        or "0"
    )


def simulate_scope(prefix: str) -> int:
    """Mirror fixed brand-head scope: first significant token LIKE entity haystack."""
    import re

    stop = {
        "ADVANCE",
        "EXTRA",
        "SINUS",
        "RELIEF",
        "COLD",
        "FLU",
        "DAY",
        "NIGHT",
        "PE",
        "FORTE",
        "PLUS",
        "MG",
        "ML",
    }
    parts = re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", prefix)
    tokens = []
    for p in parts:
        u = p.upper()
        if u in stop:
            continue
        if u not in tokens:
            tokens.append(u)
    if not tokens:
        return 0
    tok = tokens[0].replace("'", "''")
    return int(
        psql(
            "SELECT COUNT(*) FROM collection_768_2 WHERE "
            f"UPPER(COALESCE(metadata->>'entity','') || ' ' || "
            f"COALESCE(metadata->>'entity_aliases','')) LIKE '%{tok}%';"
        ).strip()
        or "0"
    )


def main() -> None:
    rows = []
    print("=== SQL corpus + scope simulation (0 Vertex) ===")
    for item in QUESTIONS:
        hits = {e: entity_count(e) for e in item["expect_entities"]}
        any_hit = any(v > 0 for v in hits.values())
        if item["expect_neg"]:
            ok = not any_hit
            mark = "PASS_NEG" if ok else "FAIL_NEG"
        else:
            ok = any_hit
            mark = "PASS" if ok else "FAIL"
        row = {"id": item["id"], "q": item["q"], "hits": hits, "sql_ok": ok, "mark": mark}
        rows.append(row)
        print(f"[{mark}] {item['id']} hits={hits}")

    scope_n = simulate_scope("Panadol Advance 500")
    print(f"[SCOPE] Panadol Advance 500 -> brand-head matches={scope_n}")

    print("\n=== /search smoke (embed only; 4s gap; stop on quota) ===")
    search_rows = []
    for item in QUESTIONS[:6]:
        time.sleep(4)
        try:
            r = requests.post(
                f"{API}/api/v1/nlp/index/search/2",
                json={"text": item["q"], "limit": 5},
                timeout=90,
            )
            body = r.json()
            ents = [
                (x.get("metadata") or {}).get("entity")
                for x in (body.get("results") or [])[:5]
            ]
            ok = r.status_code < 400 and bool(body.get("results"))
            if item["expect_neg"]:
                ok = r.status_code < 400  # may return unrelated or empty
            search_rows.append(
                {
                    "id": item["id"],
                    "http": r.status_code,
                    "signal": body.get("signal"),
                    "ents": ents,
                    "ok": ok,
                }
            )
            print(f"[{'PASS' if ok else 'FAIL'}] {item['id']} ents={ents[:3]}")
            if r.status_code == 429 or "quota" in str(body).lower():
                print("quota — stop search")
                break
        except Exception as exc:
            search_rows.append({"id": item["id"], "ok": False, "error": str(exc)})
            print(f"[FAIL] {item['id']} {exc}")
            break

    print("\n=== /answer critical 2 (heuristic parse; needs gen quota) ===")
    answer_rows = []
    for item in QUESTIONS[:2]:
        time.sleep(10)
        try:
            r = requests.post(
                f"{API}/api/v1/nlp/index/answer/2",
                json={"text": item["q"], "limit": 5},
                timeout=180,
            )
            body = r.json()
            ans = body.get("answer") or body.get("message") or ""
            answer_rows.append(
                {
                    "id": item["id"],
                    "http": r.status_code,
                    "signal": body.get("signal"),
                    "ans": ans[:400],
                }
            )
            print(f"[{body.get('signal')}] {item['id']}")
            print(" ", ans[:200].replace("\n", " "))
        except Exception as exc:
            answer_rows.append({"id": item["id"], "error": str(exc)})
            print(f"[ERR] {item['id']} {exc}")

    report = {
        "sql": rows,
        "scope_panadol_advance_matches": scope_n,
        "search": search_rows,
        "answer": answer_rows,
        "notes": [
            "RAG_SEMANTIC_PARSER_ENABLED=false during this run",
            "entity scope brand-head fix applied for Panadol Advance 500",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

"""Bulk-repair leaflet Brand entities in collection_768_2."""
from __future__ import annotations

import csv
import io
import json
import re
import subprocess
from pathlib import Path

OUT_SQL = Path(__file__).resolve().parents[1] / "eval_run" / "e2e_live_results" / "_fix_entities.sql"

BRAND_RE = re.compile(
    r"(?im)Brand:\s*(.+?)(?=\s+(?:Catalog SKU|INN\s*/\s*actives|Strength\s*/\s*form|Manufacturer)\b|\s*$)"
)

FILE_BRAND = {
    "panadol_paracetamol_500": "Panadol Advance",
    "panadol_cold_flu_day": "Panadol Cold & Flu Day",
    "panadol_sinus_relief_pe": "Panadol Sinus Relief PE",
    "panadol_extra": "Panadol Extra",
    "panadol_joint": "Panadol Joint",
    "panadol_migraine": "Panadol Migraine",
    "panadol_acute_head_cold": "Panadol Acute Head Cold",
    "panadol_cold_flu_all_in_one": "Panadol Cold & Flu All In One",
    "panadol_vapour_release": "Panadol Cold & Flu Vapour Release",
    "cetal_cold_flu_day": "Cetal Cold & Flu Day",
    "flurest_n": "Flurest-N",
    "congestal": "Congestal",
    "sine_up": "Sine-Up",
    "bradozen": "Bradozen",
    "notussil": "Notussil",
    "tussigreen": "Tussigreen",
    "daflon_500": "Daflon 500",
    "daflon_1000": "Daflon 1000",
    "controloc_20": "Controloc 20",
    "jeparilon": "Jeparilon",
    "anaseziago": "Anaseziago",
    "adol_500": "Adol",
    "cataflam_25": "Cataflam",
    "brufen_400": "Brufen",
    "antinal": "Antinal",
    "flagyl_500": "Flagyl",
    "augmentin_1g": "Augmentin",
    "hibiotic_1g": "Hi-Biotic",
    "zithrokan_500": "Zithrokan",
    "ciprobay_500": "Ciprobay",
    "risek_20": "Risek",
    "gaviscon": "Gaviscon Advance",
    "motilium_10": "Motilium",
    "buscopan": "Buscopan",
    "concor_5": "Concor",
    "norvasc_5": "Norvasc",
    "glucophage_500": "Glucophage",
    "amaryl_2": "Amaryl",
    "lipitor_20": "Lipitor",
    "plavix_75": "Plavix",
    "aspocid_75": "Aspocid",
    "telfast_120": "Telfast",
    "claritine_10": "Claritine",
    "otrivin_0_1": "Otrivin",
    "ventolin_inhaler": "Ventolin",
    "singulair_10": "Singulair",
    "diflucan_150": "Diflucan",
    "lamisil_250": "Lamisil",
    "duphaston_10": "Duphaston",
    "folic_acid_5": "Folic Acid",
    "ferrotron": "Ferrotron",
    "milga": "Milga",
    "smecta": "Smecta",
    "enterogermina": "Enterogermina",
    "strepsils": "Strepsils",
    "comtrex": "Comtrex",
}


def brand_from_file(file_name: str) -> str | None:
    base = file_name.rsplit("/", 1)[-1]
    m = re.search(r"\d{2}_([a-z0-9_]+)\.txt$", base, re.I)
    if not m:
        return None
    return FILE_BRAND.get(m.group(1).lower())


def main() -> None:
    raw = subprocess.check_output(
        [
            "docker",
            "exec",
            "pgvector",
            "psql",
            "-U",
            "postgres",
            "-d",
            "algorag",
            "-c",
            "COPY ("
            " SELECT id, coalesce(text,''), coalesce(metadata::text,'{}') "
            " FROM collection_768_2"
            ") TO STDOUT WITH CSV",
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    reader = csv.reader(io.StringIO(raw))
    updates: list[str] = []
    samples: list[str] = []
    for row in reader:
        if len(row) < 3:
            continue
        row_id, text, meta_s = row[0], row[1], row[2]
        try:
            meta = json.loads(meta_s)
        except json.JSONDecodeError:
            continue
        old = meta.get("entity")
        brand = None
        m = BRAND_RE.search(text or "")
        if m:
            brand = m.group(1).strip().strip(" .")
        if not brand:
            brand = brand_from_file(str(meta.get("file_name") or ""))
        if not brand or brand == old:
            continue
        meta["entity"] = brand
        aliases = meta.get("entity_aliases") or []
        if isinstance(aliases, list):
            low = {str(a).lower() for a in aliases}
            if brand.lower() not in low:
                aliases = [brand, *aliases]
            aliases = [a for a in aliases if str(a).lower() != "reliefmax paracetamol"]
            meta["entity_aliases"] = aliases
        meta_json = json.dumps(meta, ensure_ascii=False).replace("'", "''")
        updates.append(
            f"UPDATE collection_768_2 SET metadata = '{meta_json}'::jsonb WHERE id = {int(row_id)};"
        )
        if len(samples) < 15:
            samples.append(f"{row_id}: {old!r} -> {brand!r}")

    OUT_SQL.parent.mkdir(parents=True, exist_ok=True)
    OUT_SQL.write_text("\n".join(updates) + "\n", encoding="utf-8")
    print(f"updates={len(updates)} sql={OUT_SQL}")
    for s in samples:
        print(s)

    if updates:
        # Apply via docker cp + psql
        subprocess.check_call(
            [
                "docker",
                "cp",
                str(OUT_SQL),
                "pgvector:/tmp/_fix_entities.sql",
            ]
        )
        applied = subprocess.check_output(
            [
                "docker",
                "exec",
                "pgvector",
                "psql",
                "-U",
                "postgres",
                "-d",
                "algorag",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                "/tmp/_fix_entities.sql",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print(applied[-500:])

    print("--- entities ---")
    print(
        subprocess.check_output(
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
                "SELECT DISTINCT metadata->>'entity' FROM collection_768_2 "
                "WHERE metadata->>'entity' ~* '(Panadol|Flurest|Jeparilon|Brufen|Congestal)' "
                "ORDER BY 1;",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    )


if __name__ == "__main__":
    main()

"""Build RAG_CORPUS_56.xlsx with PRODUCTS / INTERACTIONS / ALIASES sheets."""
from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = Path(r"d:\mini-rag")
sys.path.insert(0, str(ROOT / "leaflets"))

from _apply_dosing_patch import DOSING_BY_FILE  # noqa: E402
from _apply_product_patch import PRODUCT_PATCH_BY_FILE  # noqa: E402
from _enrich_from_excel import (  # noqa: E402
    BRAND_BY_FILE,
    INN_BY_FILE,
    SKU_PREFERS,
    _clean,
    expand_inn_keys,
    load_all_material,
    load_disease_map,
    load_interactions,
    load_medicin,
    pick_sku,
    primary_materials,
)

OUT = ROOT / "excel sheets" / "RAG_CORPUS_56.xlsx"

PRODUCT_COLUMNS = [
    "sku_id",
    "file_name",
    "brand_name",
    "product_line",
    "catalog_sku",
    "inn_primary",
    "inn_all",
    "inn_aliases",
    "strength",
    "form",
    "min_age",
    "adult_dose",
    "max_daily_dose",
    "max_daily_dose_value",
    "max_daily_dose_unit",
    "pediatric_dose",
    "pediatric_min_age",
    "pediatric_max_daily_dose",
    "indications",
    "contraindications",
    "warnings",
    "side_effects_major",
    "side_effects_minor",
    "pregnancy",
    "breastfeeding",
    "storage",
    "company",
    "price",
    "category_1",
    "category_2",
    "category_3",
    "cross_selling",
    "black_box",
    "notes_hcp",
    "patient_education",
    "source",
]

PREGNANCY_VALUES = (
    "safe",
    "use_with_caution",
    "avoid",
    "contraindicated",
    "consult_physician",
    "unknown",
)
BREASTFEEDING_VALUES = PREGNANCY_VALUES

# Standardized clinical overrides keyed by leaflet file_name.
# pregnancy / breastfeeding: enum only.
# max_daily_dose*: numeric split when possible.
# pediatric_dose: fill mainly when adult_dose is empty (also kept for plain paracetamol).
CLINICAL_BY_FILE: dict[str, dict[str, str | float | int | None]] = {}


def _clin(
    *,
    pregnancy: str,
    breastfeeding: str,
    max_daily_dose: str = "",
    max_daily_dose_value: float | int | None = None,
    max_daily_dose_unit: str = "",
    pediatric_dose: str = "",
) -> dict[str, str | float | int | None]:
    assert pregnancy in PREGNANCY_VALUES, pregnancy
    assert breastfeeding in BREASTFEEDING_VALUES, breastfeeding
    return {
        "pregnancy": pregnancy,
        "breastfeeding": breastfeeding,
        "max_daily_dose": max_daily_dose,
        "max_daily_dose_value": max_daily_dose_value,
        "max_daily_dose_unit": max_daily_dose_unit,
        "pediatric_dose": pediatric_dose,
    }


def _init_clinical_overrides() -> None:
    """Populate CLINICAL_BY_FILE from curated corpus guidance."""
    plain_para = _clin(
        pregnancy="safe",
        breastfeeding="safe",
        max_daily_dose="4000 mg/day",
        max_daily_dose_value=4000,
        max_daily_dose_unit="mg/day",
        pediatric_dose="10-15 mg/kg/dose every 4-6 hours; max 60 mg/kg/day",
    )
    for f in (
        "01_panadol_paracetamol_500.txt",
        "16_adol_500.txt",
        "51_panadol_extra.txt",
        "52_panadol_joint.txt",
        "53_panadol_migraine.txt",
    ):
        CLINICAL_BY_FILE[f] = dict(plain_para)

    cold_avoid = _clin(
        pregnancy="avoid",
        breastfeeding="avoid",
        max_daily_dose="",
        max_daily_dose_value=None,
        max_daily_dose_unit="",
        pediatric_dose="Not recommended under 12 years",
    )
    for f in (
        "02_panadol_cold_flu_day.txt",
        "03_panadol_sinus_relief_pe.txt",
        "04_cetal_cold_flu_day.txt",
        "05_flurest_n.txt",
        "06_congestal.txt",
        "07_sine_up.txt",
        "50_comtrex.txt",
        "54_panadol_acute_head_cold.txt",
        "55_panadol_cold_flu_all_in_one.txt",
        "56_panadol_vapour_release.txt",
    ):
        CLINICAL_BY_FILE[f] = dict(cold_avoid)

    CLINICAL_BY_FILE["18_brufen_400.txt"] = _clin(
        pregnancy="avoid",
        breastfeeding="use_with_caution",
        max_daily_dose="2400 mg/day",
        max_daily_dose_value=2400,
        max_daily_dose_unit="mg/day",
    )
    CLINICAL_BY_FILE["17_cataflam_25.txt"] = _clin(
        pregnancy="avoid",
        breastfeeding="use_with_caution",
        max_daily_dose="150 mg/day",
        max_daily_dose_value=150,
        max_daily_dose_unit="mg/day",
    )
    CLINICAL_BY_FILE["19_antinal.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["20_flagyl_500.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["21_augmentin_1g.txt"] = _clin(
        pregnancy="use_with_caution",
        breastfeeding="use_with_caution",
    )
    CLINICAL_BY_FILE["22_hibiotic_1g.txt"] = _clin(
        pregnancy="use_with_caution",
        breastfeeding="use_with_caution",
    )
    CLINICAL_BY_FILE["23_zithrokan_500.txt"] = _clin(
        pregnancy="use_with_caution",
        breastfeeding="use_with_caution",
    )
    CLINICAL_BY_FILE["24_ciprobay_500.txt"] = _clin(
        pregnancy="contraindicated",
        breastfeeding="contraindicated",
    )
    CLINICAL_BY_FILE["25_risek_20.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["13_controloc_20.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["26_gaviscon.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["27_motilium_10.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="avoid",
    )
    CLINICAL_BY_FILE["28_buscopan.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["29_concor_5.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["30_norvasc_5.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["31_glucophage_500.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["32_amaryl_2.txt"] = _clin(
        pregnancy="contraindicated",
        breastfeeding="contraindicated",
    )
    CLINICAL_BY_FILE["33_lipitor_20.txt"] = _clin(
        pregnancy="contraindicated",
        breastfeeding="contraindicated",
    )
    CLINICAL_BY_FILE["34_plavix_75.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["35_aspocid_75.txt"] = _clin(
        pregnancy="avoid",
        breastfeeding="use_with_caution",
        max_daily_dose="75-100 mg/day (antiplatelet)",
        max_daily_dose_value=100,
        max_daily_dose_unit="mg/day",
    )
    CLINICAL_BY_FILE["36_telfast_120.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["37_claritine_10.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["38_otrivin_0_1.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["39_ventolin_inhaler.txt"] = _clin(
        pregnancy="use_with_caution",
        breastfeeding="use_with_caution",
    )
    CLINICAL_BY_FILE["40_singulair_10.txt"] = _clin(
        pregnancy="use_with_caution",
        breastfeeding="use_with_caution",
    )
    CLINICAL_BY_FILE["41_diflucan_150.txt"] = _clin(
        pregnancy="avoid",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["42_lamisil_250.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="avoid",
    )
    CLINICAL_BY_FILE["43_duphaston_10.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="avoid",
    )
    CLINICAL_BY_FILE["44_folic_acid_5.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["45_ferrotron.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["46_milga.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["47_smecta.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["48_enterogermina.txt"] = _clin(
        pregnancy="safe",
        breastfeeding="safe",
    )
    CLINICAL_BY_FILE["49_strepsils.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["08_bradozen.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["09_notussil.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["10_tussigreen.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["11_daflon_500.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["12_daflon_1000.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    # Remaining files default to unknown if not listed
    CLINICAL_BY_FILE["14_jeparilon.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )
    CLINICAL_BY_FILE["15_anaseziago.txt"] = _clin(
        pregnancy="consult_physician",
        breastfeeding="consult_physician",
    )


_init_clinical_overrides()

INTERACTION_COLUMNS = [
    "sku_id",
    "brand_name",
    "api1",
    "api2",
    "risk",
    "type",
    "monitoring",
    "dose_adjustment",
    "alternative",
    "patient_warning",
    "severity",
    "note_raw",
]

ALIAS_COLUMNS = [
    "sku_id",
    "brand_name",
    "alias",
    "alias_type",
]

# Common Arabic / misspelling aliases for Egyptian pharmacy chat
AR_ALIASES: dict[str, list[str]] = {
    "Panadol Advance": ["بانادول", "بانادول ادڤانس", "panadol"],
    "Panadol Cold & Flu Day": ["بانادول كولد", "بانادول برد"],
    "Panadol Sinus Relief PE": ["بانادول ساينس", "بانادول جيوب"],
    "Panadol Extra": ["بانادول اكسترا"],
    "Panadol Joint": ["بانادول جوينت"],
    "Panadol Migraine": ["بانادول ميغرين", "بانادول صداع نصفي"],
    "Cetal Cold & Flu Day": ["سيتال", "سيتال كولد"],
    "Flurest-N": ["فلورست", "فلورست ن", "flurest"],
    "Congestal": ["كونجستال"],
    "Sine-Up": ["ساين اب", "ساين أب"],
    "Bradozen": ["برادوزين"],
    "Notussil": ["نوتوسيل"],
    "Tussigreen": ["توسيجرين"],
    "Daflon 500": ["دافلون", "دافلون 500"],
    "Daflon 1000": ["دافلون 1000"],
    "Controloc 20": ["كونترولوك", "كنترولوك"],
    "Jeparilon": ["جيباريلون", "جيباريلون"],
    "Anaseziago": ["اناسيزياجو"],
    "Adol": ["ادول"],
    "Cataflam": ["كتافلام", "كاتافلام"],
    "Brufen": ["بروفين", "بروفن", "ايبوبروفين"],
    "Antinal": ["انتينال"],
    "Flagyl": ["فلاجيل"],
    "Augmentin": ["اوجمنتين", "أوجمنتين"],
    "Hi-Biotic": ["هاي بيوتك", "هايبيوتك"],
    "Zithrokan": ["زثروكان", "زيثروكان"],
    "Ciprobay": ["سيبروباي"],
    "Risek": ["ريسك"],
    "Gaviscon Advance": ["جافيسكون", "جافسكون"],
    "Motilium": ["موتيليوم"],
    "Buscopan": ["بسكوبان"],
    "Concor": ["كونكور"],
    "Norvasc": ["نورفاسك"],
    "Glucophage": ["جلوكوفاج"],
    "Amaryl": ["اماريل"],
    "Lipitor": ["ليبيتور", "ليبيتور"],
    "Plavix": ["بلافيكس"],
    "Aspocid": ["اسبوسيد", "أسبروسيد", "اسبرين 75"],
    "Telfast": ["تلفاست"],
    "Claritine": ["كلاريتين"],
    "Otrivin": ["اوتريفين", "أوتريفين"],
    "Ventolin": ["فنتولين"],
    "Singulair": ["سنجيولير", "سنجيولير"],
    "Diflucan": ["ديفلوكان"],
    "Lamisil": ["لاميزيل"],
    "Duphaston": ["دوفاستون"],
    "Folic Acid": ["فوليك", "حمض الفوليك"],
    "Ferrotron": ["فيروترون"],
    "Milga": ["ميلجا"],
    "Smecta": ["سمكتا"],
    "Enterogermina": ["انتروجرمينا"],
    "Strepsils": ["ستربسيلز"],
    "Comtrex": ["كومتريكس"],
}

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def _split_note(note: str) -> dict[str, str]:
    """Best-effort parse of interaction note blobs from NEW DRUG INTERACTION.xlsx."""
    text = _clean(note)
    out = {
        "risk": "",
        "type": "",
        "monitoring": "",
        "dose_adjustment": "",
        "alternative": "",
        "patient_warning": "",
        "severity": "",
        "note_raw": text,
    }
    # Heuristic labeled segments
    lower = text.lower()
    if "risk:" in lower:
        out["risk"] = _between(text, "Risk:", ["Type:", "Monitoring:", "Dosage", "Alternative", "Patient"])
    else:
        out["risk"] = text[:220]
    if "type:" in lower:
        out["type"] = _between(text, "Type:", ["Monitoring:", "Dosage", "Alternative", "Patient", "Risk:"])
    if "monitoring:" in lower:
        out["monitoring"] = _between(
            text, "Monitoring:", ["Dosage", "Alternative", "Patient", "Type:", "Risk:"]
        )
    if "dosage" in lower:
        out["dose_adjustment"] = _between(
            text, "Dosage Adjustments:", ["Alternative:", "Patient", "Monitoring:", "Type:"]
        ) or _between(text, "Dosage:", ["Alternative:", "Patient"])
    if "alternative:" in lower:
        out["alternative"] = _between(text, "Alternative:", ["Patient", "Dosage", "Monitoring:"])
    if "patient" in lower:
        out["patient_warning"] = _between(
            text, "Patient Warnings", ["Alternative:", "Dosage", "Monitoring:"]
        ) or _between(text, "Patient Warning:", ["Alternative:"])
    # contraindication-ish keywords
    if any(k in lower for k in ("avoid", "contraindic", "do not", "ممنوع")):
        out["severity"] = "yes"
    elif out["risk"]:
        out["severity"] = "caution"
    return out


def _between(text: str, start_label: str, stop_labels: list[str]) -> str:
    low = text.lower()
    start = low.find(start_label.lower())
    if start < 0:
        return ""
    start += len(start_label)
    end = len(text)
    for stop in stop_labels:
        pos = low.find(stop.lower(), start)
        if pos >= 0:
            end = min(end, pos)
    return _clean(text[start:end]).strip(" :-;")


def _style_header(ws, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(1, col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(ncols)}1"


def _autosize(ws, max_width: int = 42) -> None:
    for col in ws.columns:
        letter = get_column_letter(col[0].column)
        width = 12
        for cell in col[:80]:
            val = str(cell.value or "")
            width = min(max_width, max(width, min(max_width, len(val) + 2)))
        ws.column_dimensions[letter].width = width


def build() -> Path:
    print("Loading source sheets...")
    med_rows = load_medicin()
    materials = load_all_material()
    disease_map = load_disease_map()
    inter_map = load_interactions(limit_per_api=20)

    wb = openpyxl.Workbook()

    # --- PRODUCTS ---
    ws_p = wb.active
    ws_p.title = "PRODUCTS"
    ws_p.append(PRODUCT_COLUMNS)
    product_rows: list[dict] = []

    for file_name in sorted(SKU_PREFERS.keys()):
        sku_id = file_name.split("_", 1)[0]
        brand = BRAND_BY_FILE[file_name]
        inns = list(INN_BY_FILE.get(file_name) or [])
        sku = pick_sku(med_rows, SKU_PREFERS[file_name])
        catalog_sku = _clean(sku.get("med")) if sku else ""
        catalog_mat = primary_materials(_clean(sku.get("New Material"))) if sku else []
        inn_all = " * ".join(inns) if inns else " * ".join(catalog_mat)
        inn_primary = inns[0] if inns else (catalog_mat[0] if catalog_mat else "")

        # material/disease enrichment when available
        mat_row = None
        for key in expand_inn_keys(inns or catalog_mat):
            if key in materials:
                mat_row = materials[key]
                break
            for mk, row in materials.items():
                if key in mk or mk in key:
                    mat_row = row
                    break
            if mat_row:
                break

        disease = ""
        for key in expand_inn_keys(inns or catalog_mat):
            disease = disease_map.get(key, "")
            if disease:
                break
            for dk, dv in disease_map.items():
                if key in dk or dk in key:
                    disease = dv
                    break
            if disease:
                break

        aliases = []
        for inn in inns:
            aliases.extend(expand_inn_keys([inn])[:3])
        aliases = sorted(set(aliases))

        row = {
            "sku_id": sku_id,
            "file_name": file_name,
            "brand_name": brand,
            "product_line": brand,
            "catalog_sku": catalog_sku,
            "inn_primary": inn_primary,
            "inn_all": inn_all,
            "inn_aliases": "; ".join(aliases[:12]),
            "strength": _clean(sku.get("CONC.")) if sku else "",
            "form": _clean(sku.get("Dosage Form")) if sku else "",
            "min_age": _clean(sku.get("Min. age")) if sku else "",
            "adult_dose": _clean(sku.get("DOSE")) if sku else "",
            "max_daily_dose": "",
            "max_daily_dose_value": None,
            "max_daily_dose_unit": "",
            "pediatric_dose": "",
            "pediatric_min_age": "",
            "pediatric_max_daily_dose": "",
            "indications": _clean(mat_row.get("Approved Uses"))[:900] if mat_row else _clean(sku.get("Uses") if sku else ""),
            "contraindications": disease[:1400] if disease else "",
            "warnings": _clean(mat_row.get("NOTES"))[:700] if mat_row else "",
            "side_effects_major": _clean(mat_row.get("SIDE EFFECTS (major)"))[:600] if mat_row else "",
            "side_effects_minor": _clean(mat_row.get("SIDE EFFECTS (minor)"))[:600] if mat_row else "",
            "pregnancy": "unknown",
            "breastfeeding": "unknown",
            "storage": "Store as labeled on Egyptian pack (commonly below 25–30°C, dry, away from children).",
            "company": _clean(sku.get("Company")) if sku else "",
            "price": _clean(sku.get("Price")) if sku else "",
            "category_1": _clean(sku.get("1Category")) if sku else "",
            "category_2": _clean(sku.get("2Category")) if sku else "",
            "category_3": _clean(sku.get("3Category")) if sku else "",
            "cross_selling": _clean(sku.get("Cross-selling")) if sku else "",
            "black_box": _clean(mat_row.get("BLACK BOX"))[:700] if mat_row else "",
            "notes_hcp": _clean(mat_row.get("NOTES"))[:700] if mat_row else "",
            "patient_education": _clean(mat_row.get("PATIENT EDUCATION"))[:700] if mat_row else "",
            "source": "FINAL MEDICIN + ALL MATERIAL 1 + FINAL MATERIAL VS DISEASE + curated clinical enums",
        }

        clin = CLINICAL_BY_FILE.get(file_name) or {}
        for key in (
            "pregnancy",
            "breastfeeding",
            "max_daily_dose",
            "max_daily_dose_value",
            "max_daily_dose_unit",
            "pediatric_dose",
        ):
            if key in clin and clin[key] not in (None, ""):
                row[key] = clin[key]

        # pediatric_dose policy: prefer fill when adult_dose empty; keep curated
        # pediatric text for cold products / plain paracetamol even if adult_dose exists.
        if row["adult_dose"] and file_name not in CLINICAL_BY_FILE:
            row["pediatric_dose"] = ""
        elif row["adult_dose"] and not clin.get("pediatric_dose"):
            # curated entry without pediatric → leave blank
            row["pediatric_dose"] = ""

        dose = DOSING_BY_FILE.get(file_name)
        if dose:
            row["strength"] = dose["strength"]
            row["min_age"] = dose["min_age"]
            row["adult_dose"] = dose["adult_dose"]

        product_patch = PRODUCT_PATCH_BY_FILE.get(file_name)
        if product_patch:
            for key, value in product_patch.items():
                row[key] = value

        product_rows.append(row)
        ws_p.append([row[c] for c in PRODUCT_COLUMNS])

    _style_header(ws_p, len(PRODUCT_COLUMNS))
    _autosize(ws_p)

    # Enum validation for pregnancy / breastfeeding
    from openpyxl.worksheet.datavalidation import DataValidation

    preg_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(PREGNANCY_VALUES) + '"',
        allow_blank=False,
    )
    preg_dv.error = "Use standardized pregnancy enum"
    preg_dv.errorTitle = "Invalid pregnancy"
    bf_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(BREASTFEEDING_VALUES) + '"',
        allow_blank=False,
    )
    bf_dv.error = "Use standardized breastfeeding enum"
    bf_dv.errorTitle = "Invalid breastfeeding"
    # column letters from PRODUCT_COLUMNS
    preg_col = get_column_letter(PRODUCT_COLUMNS.index("pregnancy") + 1)
    bf_col = get_column_letter(PRODUCT_COLUMNS.index("breastfeeding") + 1)
    n = len(product_rows) + 1
    preg_dv.add(f"{preg_col}2:{preg_col}{n}")
    bf_dv.add(f"{bf_col}2:{bf_col}{n}")
    ws_p.add_data_validation(preg_dv)
    ws_p.add_data_validation(bf_dv)

    # --- INTERACTIONS ---
    ws_i = wb.create_sheet("INTERACTIONS")
    ws_i.append(INTERACTION_COLUMNS)
    inter_count = 0
    for row in product_rows:
        keys = expand_inn_keys((row["inn_all"] or "").split("*"))
        keys = [k.strip() for k in keys if k.strip()]
        seen_pairs: set[tuple[str, str]] = set()
        added = 0
        for key in keys:
            pairs = list(inter_map.get(key, []))
            if not pairs:
                for mk, mpairs in inter_map.items():
                    if key in mk or mk.startswith(key):
                        pairs = mpairs
                        key = mk
                        break
            for api2, note in pairs:
                sig = (key, api2.upper())
                if sig in seen_pairs:
                    continue
                seen_pairs.add(sig)
                parsed = _split_note(note)
                ws_i.append(
                    [
                        row["sku_id"],
                        row["brand_name"],
                        key,
                        api2,
                        parsed["risk"],
                        parsed["type"],
                        parsed["monitoring"],
                        parsed["dose_adjustment"],
                        parsed["alternative"],
                        parsed["patient_warning"],
                        parsed["severity"],
                        parsed["note_raw"],
                    ]
                )
                inter_count += 1
                added += 1
                if added >= 15:
                    break
            if added >= 15:
                break

    _style_header(ws_i, len(INTERACTION_COLUMNS))
    _autosize(ws_i, max_width=36)

    # --- ALIASES ---
    ws_a = wb.create_sheet("ALIASES")
    ws_a.append(ALIAS_COLUMNS)
    alias_count = 0
    for row in product_rows:
        brand = row["brand_name"]
        sku_id = row["sku_id"]
        base_aliases = [
            (brand, "brand"),
            (brand.lower(), "brand_lower"),
            (row["catalog_sku"], "catalog_sku") if row["catalog_sku"] else None,
            (row["inn_primary"], "inn") if row["inn_primary"] else None,
        ]
        for inn in [x.strip() for x in (row["inn_all"] or "").split("*") if x.strip()]:
            base_aliases.append((inn, "inn"))
            for key in expand_inn_keys([inn])[:4]:
                base_aliases.append((key.title() if key.islower() else key, "inn_alias"))

        for ar in AR_ALIASES.get(brand, []):
            base_aliases.append((ar, "arabic"))

        seen: set[str] = set()
        for item in base_aliases:
            if not item:
                continue
            alias, atype = item
            alias = _clean(alias)
            if not alias:
                continue
            key = alias.casefold()
            if key in seen:
                continue
            seen.add(key)
            ws_a.append([sku_id, brand, alias, atype])
            alias_count += 1

    _style_header(ws_a, len(ALIAS_COLUMNS))
    _autosize(ws_a)

    # README sheet
    ws_r = wb.create_sheet("README", 0)
    ws_r["A1"] = "RAG_CORPUS_56 — master sheets for AlgoRAG pharmacy corpus"
    ws_r["A1"].font = Font(bold=True, size=14)
    lines = [
        "",
        "Sheets:",
        "1) PRODUCTS — one row per leaflet/product (56 rows).",
        "2) INTERACTIONS — drug-drug pairs keyed by brand/sku_id + API1/API2.",
        "3) ALIASES — brand / INN / Arabic surface forms.",
        "",
        "PRODUCTS clinical enums (standardized — do NOT use free text):",
        "  pregnancy / breastfeeding ∈ {safe, use_with_caution, avoid, contraindicated, consult_physician, unknown}",
        "",
        "Dose columns:",
        "  max_daily_dose          — display string (e.g. 4000 mg/day)",
        "  max_daily_dose_value    — numeric (e.g. 4000)",
        "  max_daily_dose_unit     — unit (e.g. mg/day)",
        "  pediatric_dose          — short leaflet text; curated for key SKUs",
        "",
        "Curated pregnancy/breastfeeding/max dose applied for the 56-drug list.",
        "",
        f"Generated products: {len(product_rows)}",
        f"Generated interaction rows: {inter_count}",
        f"Generated alias rows: {alias_count}",
        f"Clinical overrides: {len(CLINICAL_BY_FILE)} files",
    ]
    for i, line in enumerate(lines, start=2):
        ws_r[f"A{i}"] = line
    ws_r.column_dimensions["A"].width = 110

    OUT.parent.mkdir(parents=True, exist_ok=True)
    targets = [OUT, OUT.with_name("RAG_CORPUS_56_v2.xlsx")]
    saved = None
    last_err = None
    for target in targets:
        try:
            wb.save(target)
            saved = target
            break
        except PermissionError as exc:
            last_err = exc
            print(f"locked, trying next: {target.name}")
    if saved is None:
        raise last_err or RuntimeError("could not save workbook")
    print(f"Wrote {saved}")
    print(f"PRODUCTS={len(product_rows)} INTERACTIONS={inter_count} ALIASES={alias_count}")
    # quick enum check
    bad = [
        (r["file_name"], r["pregnancy"], r["breastfeeding"])
        for r in product_rows
        if r["pregnancy"] not in PREGNANCY_VALUES or r["breastfeeding"] not in BREASTFEEDING_VALUES
    ]
    print("enum_violations", bad)
    return saved


if __name__ == "__main__":
    build()

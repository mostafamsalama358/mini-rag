"""Render indexable product documents from RAG_CORPUS workbook rows."""
from __future__ import annotations

import re


def _val(value: object, default: str = "-") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _slug(text: str, *, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    return slug[:max_len] or "item"


def render_interaction_line(row: dict) -> str:
    parts = [
        f"{_val(row.get('api1'))} + {_val(row.get('api2'))}",
        f"Risk: {_val(row.get('risk'), '')}",
        f"Type: {_val(row.get('type'), '')}",
        f"Monitoring: {_val(row.get('monitoring'), '')}",
        f"Dose adjustment: {_val(row.get('dose_adjustment'), '')}",
        f"Alternative: {_val(row.get('alternative'), '')}",
        f"Patient warning: {_val(row.get('patient_warning'), '')}",
    ]
    return "- " + "; ".join(part for part in parts if part.split(": ", 1)[-1])


def render_interaction_document(row: dict) -> str:
    brand = _val(row.get("brand_name"))
    lines = [
        f"Drug interaction — {brand}",
        "Corpus type: RAG_CORPUS workbook / INTERACTIONS sheet",
        f"SKU ID: {_val(row.get('sku_id'))}",
        f"Brand: {brand}",
        f"API 1: {_val(row.get('api1'))}",
        f"API 2: {_val(row.get('api2'))}",
        f"Risk: {_val(row.get('risk'))}",
        f"Type: {_val(row.get('type'))}",
        f"Monitoring: {_val(row.get('monitoring'))}",
        f"Dose adjustment: {_val(row.get('dose_adjustment'))}",
        f"Alternative: {_val(row.get('alternative'))}",
        f"Patient warning: {_val(row.get('patient_warning'))}",
        f"Severity: {_val(row.get('severity'), 'Not stated')}",
        "",
        "Clinical note:",
        _val(row.get("note_raw"), "See risk and monitoring guidance above."),
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def interaction_file_name(row: dict) -> str:
    sku_id = str(row.get("sku_id") or "00").zfill(2)
    api1 = _slug(_val(row.get("api1"), "api1"))
    api2 = _slug(_val(row.get("api2"), "api2"))
    return f"interactions/{sku_id}_{api1}__{api2}.txt"


def render_alias_document(brand: str, sku_id: str, aliases: list[dict]) -> str:
    lines = [
        f"Alias registry — {brand}",
        "Corpus type: RAG_CORPUS workbook / ALIASES sheet",
        f"SKU ID: {sku_id}",
        f"Brand: {brand}",
        "",
        "Known aliases:",
    ]
    for row in aliases:
        alias = _val(row.get("alias"))
        alias_type = _val(row.get("alias_type"))
        lines.append(f"- {alias} ({alias_type})")
    lines.extend(
        [
            "",
            "Retrieval hint: map user surface forms (brand, INN, Arabic, catalog SKU) to this product.",
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def alias_file_name(brand: str, sku_id: str) -> str:
    return f"aliases/{sku_id.zfill(2)}_{_slug(brand)}_aliases.txt"


def render_product(product: dict, interactions: list[dict]) -> str:
    brand = _val(product.get("brand_name"))
    catalog_sku = _val(product.get("catalog_sku"))
    categories = " > ".join(
        _val(product.get(key), "")
        for key in ("category_1", "category_2", "category_3")
        if _val(product.get(key), "")
    ) or "-"

    interaction_block = "\n".join(render_interaction_line(row) for row in interactions[:5])
    if not interaction_block:
        interaction_block = "- No interaction rows in workbook for this SKU."
    else:
        interaction_block += "\n- See dedicated interaction documents in the workbook corpus for full pairs."

    lines = [
        catalog_sku,
        "Patient Information Leaflet — Egyptian Commercial E2E Corpus (RAG_CORPUS workbook)",
        f"Brand: {brand}",
        f"Product line: {_val(product.get('product_line'))}",
        f"Catalog SKU: {catalog_sku}",
        f"SKU ID: {_val(product.get('sku_id'))}",
        f"INN / actives: {_val(product.get('inn_all'))}",
        f"INN primary: {_val(product.get('inn_primary'))}",
        f"INN aliases: {_val(product.get('inn_aliases'))}",
        f"Strength / form: {_val(product.get('strength'))} | Form={_val(product.get('form'))} | Min.age={_val(product.get('min_age'))}",
        f"Manufacturer / market: {_val(product.get('company'))}",
        f"Price (catalog): {_val(product.get('price'))}",
        f"Categories: {categories}",
        f"Source workbook: {_val(product.get('source'), 'RAG_CORPUS_56.product_patched.xlsx')}",
        "",
        f"1. What {brand} is used for",
        _val(product.get("indications")),
        "",
        "2. Dosage — Adults",
        f"Adult dose: {_val(product.get('adult_dose'))}",
        f"Maximum daily dose: {_val(product.get('max_daily_dose'))} ({_val(product.get('max_daily_dose_value'))} {_val(product.get('max_daily_dose_unit'))})",
        "",
        "3. Dosage — Children",
        f"Minimum age in catalog: {_val(product.get('min_age'))}",
        f"Pediatric min age: {_val(product.get('pediatric_min_age'), 'See pack')}",
        f"Pediatric dose: {_val(product.get('pediatric_dose'), 'See pack')}",
        f"Pediatric max daily dose: {_val(product.get('pediatric_max_daily_dose'), 'See pack')}",
        "",
        f"4. Do not take {brand} if / disease cautions",
        _val(product.get("contraindications"), "See pack contraindications"),
        "",
        "5. Warnings and precautions",
        f"BLACK BOX / serious warnings: {_val(product.get('black_box'), 'None listed')}",
        f"Warnings: {_val(product.get('warnings'), 'None listed')}",
        f"HCP notes: {_val(product.get('notes_hcp'), 'None listed')}",
        f"Patient education: {_val(product.get('patient_education'), 'Follow pharmacist counseling')}",
        "",
        "6. Interactions (from workbook INTERACTIONS sheet)",
        interaction_block,
        "",
        "7. Pregnancy",
        f"Pregnancy safety: {_val(product.get('pregnancy'))}",
        "",
        "8. Breastfeeding",
        f"Breastfeeding safety: {_val(product.get('breastfeeding'))}",
        "",
        "9. Supplements / cross-selling",
        f"Catalog cross-selling: {_val(product.get('cross_selling'), 'None listed')}",
        "",
        "10. Possible side effects",
        f"Major: {_val(product.get('side_effects_major'), 'See pack')}",
        f"Minor: {_val(product.get('side_effects_minor'), 'See pack')}",
        "",
        "11. Storage",
        _val(product.get("storage"), "Store as labeled on the Egyptian pack."),
        "",
    ]
    return "\n".join(lines).strip() + "\n"

"""OpenDataLoader PDF adapter → DocumentModel StructuralElements.

Local (non-hybrid-server) mode only: requires ``opendataloader-pdf`` + Java 11+.
When unavailable, callers MUST fall back to the legacy PyMuPDF/OCR path.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from core.document_intelligence.model import StructuralElement, make_element_id

logger = logging.getLogger(__name__)

_SKIP_TYPES = frozenset({"header", "footer", "page", "document"})


def is_opendataloader_available() -> bool:
    """True when the Python package and a usable Java runtime are present."""
    try:
        import opendataloader_pdf  # noqa: F401
    except Exception:
        return False
    return _java_available()


def _java_available() -> bool:
    java_bin = shutil.which("java")
    if not java_bin:
        return False
    try:
        result = subprocess.run(
            [java_bin, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def convert_pdf_to_json(pdf_path: str) -> dict[str, Any]:
    """Run OpenDataLoader local convert and return the parsed JSON document."""
    import opendataloader_pdf

    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(pdf_path)

    with tempfile.TemporaryDirectory(prefix="odl_pdf_") as tmp:
        out_dir = Path(tmp)
        logger.info("OpenDataLoader convert start | file=%s", pdf_path)
        opendataloader_pdf.convert(
            input_path=[str(pdf.resolve())],
            output_dir=str(out_dir),
            format="json",
        )
        json_path = _resolve_json_output(out_dir, pdf)
        raw = json_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(f"OpenDataLoader JSON root must be object, got {type(data)!r}")
        logger.info(
            "OpenDataLoader convert done | file=%s pages=%s kids=%s",
            pdf_path,
            data.get("number of pages"),
            len(data.get("kids") or []),
        )
        return data


def _resolve_json_output(out_dir: Path, pdf: Path) -> Path:
    preferred = out_dir / f"{pdf.stem}.json"
    if preferred.is_file():
        return preferred
    matches = sorted(out_dir.rglob("*.json"))
    if not matches:
        raise FileNotFoundError(f"OpenDataLoader produced no JSON under {out_dir}")
    return matches[0]


def json_to_structural_elements(
    odl_doc: dict[str, Any],
    *,
    file_id: str,
) -> list[StructuralElement]:
    """Map OpenDataLoader JSON kids tree into canonical StructuralElements."""
    elements: list[StructuralElement] = []
    order = 0
    kids = odl_doc.get("kids") or []
    if not isinstance(kids, list):
        return elements

    for node in kids:
        order = _walk_node(
            node,
            file_id=file_id,
            elements=elements,
            order=order,
            parent_id=None,
            path_prefix="root",
        )
    return elements


def covered_page_numbers(elements: list[StructuralElement]) -> set[int]:
    pages: set[int] = set()
    for el in elements:
        page = (el.provenance or {}).get("page")
        if isinstance(page, int) and page > 0:
            pages.add(page)
    return pages


def _walk_node(
    node: Any,
    *,
    file_id: str,
    elements: list[StructuralElement],
    order: int,
    parent_id: str | None,
    path_prefix: str,
) -> int:
    if not isinstance(node, dict):
        return order

    raw_type = str(node.get("type") or "").strip().lower()
    page_num = _as_int(node.get("page number"))
    node_id = node.get("id")
    path = f"{path_prefix}/{raw_type or 'node'}:{node_id if node_id is not None else order}"

    if raw_type in _SKIP_TYPES:
        # Drop headers/footers (and nested noise) entirely — do not recurse.
        return order

    if raw_type in {"heading", "title"}:
        text = _node_text(node)
        if text:
            el_id = make_element_id(file_id, path)
            elements.append(
                StructuralElement(
                    id=el_id,
                    type="heading",
                    order=order,
                    text=text,
                    provenance=_prov(file_id, page_num, raw_type, node),
                    parent_id=parent_id,
                )
            )
            order += 1
        return order

    if raw_type in {"paragraph", "caption", "formula", "text", "text block", "textblock"}:
        text = _node_text(node)
        # text block may nest kids without content on itself
        if text:
            el_type = "paragraph"
            el_id = make_element_id(file_id, path)
            elements.append(
                StructuralElement(
                    id=el_id,
                    type=el_type,
                    order=order,
                    text=text,
                    provenance=_prov(file_id, page_num, raw_type, node),
                    parent_id=parent_id,
                )
            )
            order += 1
            parent_id = el_id
        for child in node.get("kids") or []:
            order = _walk_node(
                child,
                file_id=file_id,
                elements=elements,
                order=order,
                parent_id=parent_id,
                path_prefix=path,
            )
        return order

    if raw_type == "list":
        list_id = make_element_id(file_id, path)
        list_text = _node_text(node) or f"list:{node.get('number of list items') or ''}"
        elements.append(
            StructuralElement(
                id=list_id,
                type="list",
                order=order,
                text=list_text.strip() or "list",
                provenance=_prov(file_id, page_num, raw_type, node),
                parent_id=parent_id,
            )
        )
        order += 1
        items = node.get("list items") or node.get("kids") or []
        for idx, item in enumerate(items, start=1):
            order = _walk_list_item(
                item,
                file_id=file_id,
                elements=elements,
                order=order,
                parent_id=list_id,
                path_prefix=f"{path}/item:{idx}",
                page_num=page_num,
            )
        return order

    if raw_type == "list item":
        return _walk_list_item(
            node,
            file_id=file_id,
            elements=elements,
            order=order,
            parent_id=parent_id,
            path_prefix=path,
            page_num=page_num,
        )

    if raw_type == "table":
        return _walk_table(
            node,
            file_id=file_id,
            elements=elements,
            order=order,
            parent_id=parent_id,
            path_prefix=path,
            page_num=page_num,
        )

    if raw_type in {"image", "picture", "figure"}:
        caption = _node_text(node) or str(node.get("description") or "").strip()
        el_id = make_element_id(file_id, path)
        elements.append(
            StructuralElement(
                id=el_id,
                type="figure-placeholder",
                order=order,
                text=caption,
                provenance=_prov(file_id, page_num, raw_type, node),
                parent_id=parent_id,
            )
        )
        return order + 1

    # Unknown container / leaf: prefer content, else recurse kids.
    text = _node_text(node)
    if text:
        el_id = make_element_id(file_id, path)
        elements.append(
            StructuralElement(
                id=el_id,
                type="section",
                order=order,
                text=text,
                provenance=_prov(file_id, page_num, raw_type or "unknown", node),
                parent_id=parent_id,
            )
        )
        order += 1
        parent_id = el_id

    for child in node.get("kids") or []:
        order = _walk_node(
            child,
            file_id=file_id,
            elements=elements,
            order=order,
            parent_id=parent_id,
            path_prefix=path,
        )
    return order


def _walk_list_item(
    node: Any,
    *,
    file_id: str,
    elements: list[StructuralElement],
    order: int,
    parent_id: str | None,
    path_prefix: str,
    page_num: int | None,
) -> int:
    if not isinstance(node, dict):
        return order
    text = _node_text(node)
    if not text:
        # nested content only
        for child in node.get("kids") or []:
            order = _walk_node(
                child,
                file_id=file_id,
                elements=elements,
                order=order,
                parent_id=parent_id,
                path_prefix=path_prefix,
            )
        return order

    el_id = make_element_id(file_id, path_prefix)
    elements.append(
        StructuralElement(
            id=el_id,
            type="list-item",
            order=order,
            text=text,
            provenance=_prov(file_id, page_num or _as_int(node.get("page number")), "list item", node),
            parent_id=parent_id,
        )
    )
    order += 1
    for child in node.get("kids") or []:
        order = _walk_node(
            child,
            file_id=file_id,
            elements=elements,
            order=order,
            parent_id=el_id,
            path_prefix=path_prefix,
        )
    return order


def _walk_table(
    node: dict[str, Any],
    *,
    file_id: str,
    elements: list[StructuralElement],
    order: int,
    parent_id: str | None,
    path_prefix: str,
    page_num: int | None,
) -> int:
    table_id = make_element_id(file_id, path_prefix)
    rows = node.get("rows") or []
    summary_parts: list[str] = []
    row_elements: list[StructuralElement] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_num = _as_int(row.get("row number")) or (len(row_elements) + 1)
        fields = _row_fields(row)
        if not fields:
            continue
        summary_parts.append(" | ".join(fields.values()))
        row_elements.append(
            StructuralElement(
                id=make_element_id(file_id, f"{path_prefix}/row:{row_num}"),
                type="table-row",
                order=0,  # fixed below
                fields=fields,
                provenance={
                    "page": page_num,
                    "row_index": row_num,
                    "file_name": file_id,
                    "parser": "opendataloader",
                },
                parent_id=table_id,
            )
        )

    table_text = _node_text(node) or ("\n".join(summary_parts) if summary_parts else "table")
    elements.append(
        StructuralElement(
            id=table_id,
            type="table",
            order=order,
            text=table_text,
            provenance=_prov(file_id, page_num, "table", node),
            parent_id=parent_id,
        )
    )
    order += 1
    for row_el in row_elements:
        row_el.order = order
        elements.append(row_el)
        order += 1
    return order


def _row_fields(row: dict[str, Any]) -> dict[str, str]:
    cells = row.get("cells") or []
    fields: dict[str, str] = {}
    for cell in cells:
        if not isinstance(cell, dict):
            continue
        col = _as_int(cell.get("column number")) or (len(fields) + 1)
        text = _collect_text(cell).strip()
        if not text:
            continue
        fields[f"col_{col}"] = text
    return fields


def _node_text(node: dict[str, Any]) -> str:
    content = node.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    description = node.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return ""


def _collect_text(node: dict[str, Any]) -> str:
    parts: list[str] = []
    direct = _node_text(node)
    if direct:
        parts.append(direct)
    for child in node.get("kids") or []:
        if isinstance(child, dict):
            nested = _collect_text(child)
            if nested:
                parts.append(nested)
    return " ".join(parts)


def _prov(
    file_id: str,
    page_num: int | None,
    raw_type: str,
    node: dict[str, Any],
) -> dict[str, Any]:
    prov: dict[str, Any] = {
        "file_name": file_id,
        "parser": "opendataloader",
        "odl_type": raw_type,
    }
    if page_num is not None:
        prov["page"] = page_num
    bbox = node.get("bounding box")
    if isinstance(bbox, list) and len(bbox) == 4:
        prov["bbox"] = bbox
    return prov


def _as_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None

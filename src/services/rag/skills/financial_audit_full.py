"""Full-file GRC financial audit: load every Excel/CSV row + deterministic RULE-*.

Vector top-k cannot see a whole journal workbook. This module loads all
table-row chunks from Postgres and evaluates RULE-TAX/CRD/CUT/FRD in code,
then returns the Skill JSON report (LLM optional / not required for issues).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from models.db_schemes import RetrievedDocument
from repositories.chunk_repository import ChunkModel

logger = logging.getLogger("uvicorn.error")

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"none", "null", "nan", "-"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def _fields_of(doc: RetrievedDocument) -> dict[str, Any]:
    md = doc.metadata or {}
    fields = md.get("fields")
    if isinstance(fields, dict) and fields:
        return fields
    # Fallback: col_* keys written by the spreadsheet parser.
    out: dict[str, Any] = {}
    for key, value in md.items():
        if isinstance(key, str) and key.startswith("col_") and value not in (None, ""):
            out[key[4:]] = value
    return out


def _row_identity(fields: dict[str, Any], doc: RetrievedDocument) -> tuple[str, str]:
    number = str(
        fields.get("Number")
        or fields.get("Invoice")
        or (doc.metadata or {}).get("chunk_id")
        or "unknown"
    ).strip()
    partner = str(
        fields.get("Invoice Partner Display Name")
        or fields.get("Partner")
        or fields.get("Customer")
        or ""
    ).strip()
    return number, partner


def _dedupe_transaction_docs(documents: list[RetrievedDocument]) -> list[RetrievedDocument]:
    """Keep one row per invoice Number (latest asset/chunk wins) across re-uploads."""
    best: dict[str, RetrievedDocument] = {}
    order: list[str] = []
    for doc in documents:
        fields = _fields_of(doc)
        number, _partner = _row_identity(fields, doc)
        key = number.strip().upper() if number else ""
        if not key or key == "UNKNOWN":
            # Fall back to stable chunk id so blank numbers are not collapsed.
            key = f"CHUNK:{(doc.metadata or {}).get('chunk_id') or id(doc)}"
        md = doc.metadata or {}
        asset_id = int(md.get("asset_id") or 0)
        chunk_order = int(md.get("chunk_order") or 0)
        prev = best.get(key)
        if prev is None:
            best[key] = doc
            order.append(key)
            continue
        prev_md = prev.metadata or {}
        prev_asset = int(prev_md.get("asset_id") or 0)
        prev_order = int(prev_md.get("chunk_order") or 0)
        if (asset_id, chunk_order) >= (prev_asset, prev_order):
            best[key] = doc
    return [best[k] for k in order]


def scan_transaction_issues(
    documents: list[RetrievedDocument],
    *,
    as_of: datetime | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Evaluate RULE-* against every transaction document. Returns (issues, reviewed)."""
    tx_docs = [
        d
        for d in documents
        if str((d.metadata or {}).get("source_type") or "").lower()
        in {"xlsx", "xls", "csv"}
        or str((d.metadata or {}).get("element_type") or "").lower() == "table-row"
    ]
    tx_docs = _dedupe_transaction_docs(tx_docs)
    as_of = as_of or datetime.now(timezone.utc).replace(tzinfo=None)
    issues: list[dict[str, Any]] = []

    # Pre-scan for fraud: partner + untaxed + invoice date
    fraud_index: dict[tuple[str, float], list[tuple[str, datetime]]] = {}
    parsed_rows: list[dict[str, Any]] = []

    for doc in tx_docs:
        fields = _fields_of(doc)
        number, partner = _row_identity(fields, doc)
        tax = _parse_float(fields.get("Tax"))
        untaxed = _parse_float(
            fields.get("Untaxed Amount")
            or fields.get("Untaxed Amount Signed Currency")
        )
        tax_id = str(
            fields.get("Partner/Tax ID")
            or fields.get("Partner/Partner with same Tax ID/Tax ID")
            or ""
        ).strip()
        status_pay = str(fields.get("Status In Payment") or "").strip()
        status = str(fields.get("Status") or "").strip()
        due = _parse_date(fields.get("Due Date"))
        invoice_date = _parse_date(
            fields.get("Invoice/Bill Date") or fields.get("Posting Date")
        )
        parsed_rows.append(
            {
                "number": number,
                "partner": partner,
                "tax": tax,
                "untaxed": untaxed,
                "tax_id": tax_id,
                "status_pay": status_pay,
                "status": status,
                "due": due,
                "invoice_date": invoice_date,
            }
        )
        if partner and untaxed is not None and invoice_date is not None:
            fraud_index.setdefault((partner.upper(), round(untaxed, 2)), []).append(
                (number, invoice_date)
            )

    for row in parsed_rows:
        number = row["number"]
        partner = row["partner"]

        if not row["tax_id"] or row["tax_id"].lower() in {"none", "null", "nan", "-"}:
            issues.append(
                {
                    "transaction_id": number,
                    "partner": partner,
                    "violation_type": "Missing Partner Tax ID",
                    "risk_level": "High",
                    "rule_id": "RULE-TAX-001",
                    "regulatory_reference": "Internal Bylaw — Partner Tax Compliance",
                    "root_cause": "Partner/Tax ID is empty or invalid.",
                    "corrective_action": "Capture a valid Partner/Tax ID before posting.",
                    "subskill": "tax_compliance",
                }
            )

        tax = row["tax"]
        untaxed = row["untaxed"]
        if tax is not None and untaxed is not None and untaxed != 0:
            expected = round(untaxed * 0.14, 2)
            if abs(tax - expected) > 0.05:
                issues.append(
                    {
                        "transaction_id": number,
                        "partner": partner,
                        "violation_type": "VAT calculation error",
                        "risk_level": "Medium",
                        "rule_id": "RULE-TAX-002",
                        "regulatory_reference": "Internal Bylaw — VAT equation",
                        "root_cause": (
                            f"Tax ({tax}) differs from Untaxed Amount ({untaxed}) × 0.14 "
                            f"(expected {expected}). No exemption recorded in row fields."
                        ),
                        "corrective_action": (
                            f"Set Tax to {expected} or attach a valid tax exemption."
                        ),
                        "subskill": "tax_compliance",
                    }
                )

        if re.search(r"not\s*paid", row["status_pay"], flags=re.IGNORECASE) and row["due"]:
            days_overdue = (as_of.date() - row["due"].date()).days
            if days_overdue > 15:
                issues.append(
                    {
                        "transaction_id": number,
                        "partner": partner,
                        "violation_type": "Credit overdue",
                        "risk_level": "High",
                        "rule_id": "RULE-CRD-001",
                        "regulatory_reference": "Internal Bylaw — Credit policy",
                        "root_cause": (
                            f"Status In Payment is Not Paid and Due Date is "
                            f"{days_overdue} days past as of {as_of.date().isoformat()}."
                        ),
                        "corrective_action": "Block new credit / collect overdue receivable.",
                        "subskill": "credit_policy",
                    }
                )

        if re.search(r"draft", row["status"], flags=re.IGNORECASE) and row["invoice_date"]:
            age_days = (as_of.date() - row["invoice_date"].date()).days
            if age_days > 5:
                issues.append(
                    {
                        "transaction_id": number,
                        "partner": partner,
                        "violation_type": "Cut-off / draft aging",
                        "risk_level": "Low",
                        "rule_id": "RULE-CUT-001",
                        "regulatory_reference": "Internal Bylaw — Cut-off integrity",
                        "root_cause": (
                            f"Status is Draft and invoice age is {age_days} days (> 5)."
                        ),
                        "corrective_action": "Post or cancel the draft in the correct period.",
                        "subskill": "cutoff_integrity",
                    }
                )

    # Fraud: same partner + untaxed within 48h on different invoice numbers
    seen_pairs: set[tuple[str, str]] = set()
    for (partner_key, amount), entries in fraud_index.items():
        if len(entries) < 2:
            continue
        entries_sorted = sorted(entries, key=lambda item: item[1])
        for i, (num_a, dt_a) in enumerate(entries_sorted):
            for num_b, dt_b in entries_sorted[i + 1 :]:
                if num_a == num_b:
                    continue
                delta_h = abs((dt_b - dt_a).total_seconds()) / 3600.0
                if delta_h <= 48:
                    pair_key = tuple(sorted((num_a, num_b)))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    issues.append(
                        {
                            "transaction_id": num_a,
                            "partner": partner_key.title() if partner_key else "",
                            "violation_type": "Possible duplicate / split invoice",
                            "risk_level": "Critical",
                            "rule_id": "RULE-FRD-001",
                            "regulatory_reference": "Internal Bylaw — Fraud prevention",
                            "root_cause": (
                                f"Same partner + Untaxed Amount ({amount}) within "
                                f"{delta_h:.1f}h for {num_a} and {num_b}."
                            ),
                            "corrective_action": "Hold both invoices for internal review.",
                            "subskill": "fraud_detection",
                        }
                    )

    return issues, len(tx_docs)


def build_deterministic_audit_report(
    documents: list[RetrievedDocument],
    *,
    language: str = "en",
) -> dict[str, Any]:
    issues, reviewed = scan_transaction_issues(documents)
    dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for issue in issues:
        level = str(issue.get("risk_level") or "").strip().lower()
        if level in dist:
            dist[level] += 1

    if language.startswith("ar"):
        if not issues:
            assessment = (
                f"تم مراجعة {reviewed} معاملة. لم تُرصد مخالفات مؤكدة وفق قواعد اللائحة."
            )
            recommendations = [
                "الاستمرار في مراقبة معادلة الضريبة 14% عند الإدخال.",
                "التحقق الدوري من اكتمال Partner/Tax ID قبل التثبيت.",
            ]
        else:
            assessment = (
                f"تم مراجعة {reviewed} معاملة؛ وُجدت {len(issues)} مخالفة "
                f"(Critical={dist['critical']}, High={dist['high']}, "
                f"Medium={dist['medium']}, Low={dist['low']})."
            )
            recommendations = [
                "معالجة مخالفات RULE-TAX فوراً قبل إغلاق الفترة.",
                "مراجعة المتأخرات الائتمانية والمسودات المعلقة حسب RULE-CRD/CUT.",
                "إحالة أي تكرار محتمل (RULE-FRD) للمراجع الداخلي.",
            ]
    else:
        if not issues:
            assessment = (
                f"Reviewed {reviewed} transactions. No confirmed violations under bylaw rules."
            )
            recommendations = [
                "Keep automated 14% VAT checks at posting time.",
                "Continue validating Partner/Tax ID before posting.",
            ]
        else:
            assessment = (
                f"Reviewed {reviewed} transactions; found {len(issues)} violation(s) "
                f"(Critical={dist['critical']}, High={dist['high']}, "
                f"Medium={dist['medium']}, Low={dist['low']})."
            )
            recommendations = [
                "Remediate RULE-TAX findings before period close.",
                "Review overdue credit and aged drafts (RULE-CRD / RULE-CUT).",
                "Escalate possible duplicates (RULE-FRD) to internal audit.",
            ]

    by_sub: dict[str, list] = {
        "tax_compliance": [],
        "credit_policy": [],
        "cutoff_integrity": [],
        "fraud_detection": [],
        "audit_report": [],
    }
    for issue in issues:
        key = str(issue.get("subskill") or "")
        if key in by_sub:
            by_sub[key].append(issue["transaction_id"])

    return {
        "executive_summary": {
            "transactions_reviewed": reviewed,
            "violations_found": len(issues),
            "risk_distribution": dist,
            "overall_compliance_assessment": assessment,
        },
        "issues": issues,
        "recommendations": recommendations,
        "subskill_results": {
            k: {"issue_count": len(v), "transaction_ids": v} for k, v in by_sub.items()
        },
    }


async def load_full_audit_documents(
    *,
    project_id: int,
    db_client,
    transaction_limit: int = 5000,
    policy_limit: int = 40,
) -> list[RetrievedDocument]:
    chunk_model = await ChunkModel.create_instance(db_client)
    tx_rows = await chunk_model.list_transaction_table_rows(
        project_id, limit=transaction_limit
    )
    policy_rows = await chunk_model.list_bylaw_policy_chunks(
        project_id, limit=policy_limit
    )
    docs: list[RetrievedDocument] = []
    for row in tx_rows:
        docs.append(
            RetrievedDocument(text=row["text"], score=1.0, metadata=row["metadata"])
        )
    for row in policy_rows:
        docs.append(
            RetrievedDocument(text=row["text"], score=0.5, metadata=row["metadata"])
        )
    logger.info(
        "financial_audit_full_fetch project_id=%s transactions=%s policy=%s",
        project_id,
        len(tx_rows),
        len(policy_rows),
    )
    return docs


def report_to_answer_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)

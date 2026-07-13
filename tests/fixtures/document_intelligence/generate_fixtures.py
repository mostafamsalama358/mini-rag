"""Generate golden fixtures for Document Intelligence tests (spec 006 R10)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent


def generate() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)

    # sample.txt
    (ROOT / "sample.txt").write_text(
        "First paragraph about alpha.\n\nSecond paragraph about beta.\n\nThird paragraph about gamma.\n",
        encoding="utf-8",
    )

    # sample.csv — 10 data rows
    csv_lines = ["Name,Value"]
    for i in range(1, 11):
        csv_lines.append(f"item_{i},{i * 10}")
    (ROOT / "sample.csv").write_text("\n".join(csv_lines) + "\n", encoding="utf-8")

    # sample_50_rows.xlsx
    try:
        import pandas as pd

        df = pd.DataFrame(
            {
                "Drug": [f"drug_{i}" for i in range(1, 51)],
                "Strength": [f"{i}mg" for i in range(1, 51)],
            }
        )
        df.to_excel(ROOT / "sample_50_rows.xlsx", index=False)

        # malformed.xlsx: headers only, no data rows
        empty = pd.DataFrame(columns=["A", "B"])
        empty.to_excel(ROOT / "malformed.xlsx", index=False)
    except Exception as exc:
        raise SystemExit(f"pandas/openpyxl required to generate xlsx fixtures: {exc}") from exc

    # sample_with_table.pdf — simple multi-column text table via PyMuPDF.
    pdf_path = ROOT / "sample_with_table.pdf"
    table_text = (
        "Name          Value\n"
        "alpha         10\n"
        "beta          20\n"
        "gamma         30\n"
    )
    try:
        import fitz  # PyMuPDF

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), table_text, fontsize=11)
        doc.save(pdf_path)
        doc.close()
    except Exception:
        pdf_path.write_bytes(
            b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
            + table_text.encode("latin-1", errors="replace")
        )

    # unreadable.pdf — truncated / not a real PDF
    (ROOT / "unreadable.pdf").write_bytes(b"%PDF-1.4\n% corrupted truncated")

    print(f"Fixtures written under {ROOT}")


if __name__ == "__main__":
    generate()

"""Sample GRC corpus structure for metadata/chunking recommendations."""
from __future__ import annotations

import re
from pathlib import Path

import fitz

ROOT = Path(r"d:\mini-rag\src\fields\GRC\Corpus")
OUT = Path(r"d:\mini-rag\eval_run\e2e_live_results\_grc_corpus_sample.txt")

HEAD = re.compile(
    r"^(Chapter|CHAPTER|Article|ARTICLE|Component|Principle|IFRS|IAS|"
    r"Section|PART|Part|مادة|الفصل|الباب|البند|المادة)\b",
    re.I,
)
NUM = re.compile(r"^(?:\d+(?:\.\d+){0,3})\s+\S")


def main() -> None:
    lines: list[str] = []
    for pdf in sorted(ROOT.glob("*.pdf")):
        doc = fitz.open(pdf)
        meta = doc.metadata or {}
        lines.append("=" * 60)
        lines.append(f"FILE: {pdf.name}")
        lines.append(
            f"pages={len(doc)} title={meta.get('title')!r} author={meta.get('author')!r}"
        )
        hits: list[str] = []
        empty = 0
        for i in range(len(doc)):
            t = doc[i].get_text() or ""
            if len(t.strip()) < 10:
                empty += 1
            for ln in t.splitlines():
                s = ln.strip()
                if not s or len(s) > 160:
                    continue
                if HEAD.search(s) or (NUM.match(s) and len(s) < 100):
                    hits.append(f"p{i + 1}: {s}")
        lines.append(f"empty_or_image_pages≈{empty} structure_hits={len(hits)}")
        for h in hits[:50]:
            lines.append("  " + h)
        sample_idxs = {0, 1, min(2, len(doc) - 1), len(doc) // 4, len(doc) // 2, len(doc) - 1}
        for i in sorted(sample_idxs):
            if i < 0 or i >= len(doc):
                continue
            t = (doc[i].get_text() or "").strip()
            lines.append(f"--- page {i + 1} chars={len(t)} searchable={len(t) >= 10} ---")
            lines.append(t[:1800])
            lines.append("")
        doc.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()

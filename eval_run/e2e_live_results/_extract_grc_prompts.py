"""Extract text from e:\\GRC Instructions + bylaw for GRC skill authoring."""
from __future__ import annotations

from pathlib import Path

import fitz

OUT = Path(r"d:\mini-rag\eval_run\e2e_live_results\_grc_instructions_bylaw.txt")
FILES = [
    Path(r"e:\GRC\Instructions.pdf"),
    *Path(r"e:\GRC").glob("*داخلة*.pdf"),
    *Path(r"e:\GRC").glob("*داخلية*.pdf"),
]


def main() -> None:
    lines: list[str] = []
    seen: set[str] = set()
    for path in FILES:
        if not path.is_file() or path.name in seen:
            continue
        seen.add(path.name)
        doc = fitz.open(path)
        lines.append("=" * 70)
        lines.append(f"FILE: {path}")
        lines.append(f"pages={len(doc)}")
        for i in range(len(doc)):
            text = (doc[i].get_text() or "").strip()
            lines.append(f"--- page {i + 1} chars={len(text)} ---")
            lines.append(text)
            lines.append("")
        doc.close()
    # also list all pdfs
    lines.append("=" * 70)
    lines.append("DIR LISTING:")
    for p in sorted(Path(r"e:\GRC").iterdir()):
        lines.append(f"  {p.name} ({p.stat().st_size})")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} bytes={OUT.stat().st_size} files={len(seen)}")


if __name__ == "__main__":
    main()

import re
import subprocess

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
        "-t",
        "-A",
        "-c",
        "SELECT left(text,500) FROM collection_768_2 WHERE text ILIKE '%Brand: Panadol%' LIMIT 1;",
    ],
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("REPR:", repr(raw[:600]))
for name, pat in [
    ("simple", r"(?i)Brand:\s*([^\n]+)"),
    ("stop", r"(?im)Brand:\s*(.+?)(?=\s+Catalog SKU)"),
    ("full", r"(?im)(?:^|\n)\s*Brand:\s*(.+?)(?=\s+(?:Catalog SKU|INN\s*/\s*actives|Strength\s*/\s*form|Manufacturer)\b|\s*$)"),
]:
    m = re.search(pat, raw)
    print(name, "=>", repr(m.group(1) if m else None))

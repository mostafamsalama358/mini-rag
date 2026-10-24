import json
from pathlib import Path

rows = json.loads(Path("eval_run/probe_quran_g7.json").read_text(encoding="utf-8"))
lines = []
for row in rows:
    flag = "MISS" if row.get("looks_like_miss") else "ok"
    answer = (row.get("answer") or "").replace("\n", " ")
    lines.append(
        f"{row['id']} {flag} kp={row.get('key_point_score')} {row.get('skill_id')} signal={row.get('signal')}\n{answer}\n"
    )
Path("eval_run/_quran_brief.txt").write_text("\n".join(lines), encoding="utf-8")
print("wrote", len(rows))

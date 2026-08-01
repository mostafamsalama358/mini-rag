"""T016 — every production concern on capability cards has exactly one Owner."""

from __future__ import annotations

import re

from tests.architecture._repo import GOV, markdown_table_rows, read


def _required_concerns_from_cards() -> set[str]:
    text = read(GOV / "capability-cards.md")
    concerns: set[str] = set()
    for match in re.finditer(r"`([a-z][a-z0-9_]*)`", text):
        token = match.group(1)
        # Filter contract roles and noise by requiring snake_case concern-like tokens
        # that appear in Required Concerns lines context — take all backtick tokens
        # listed on Required Concerns rows.
        concerns.add(token)
    # Keep only those that appear in ownership registry as concern_id
    return concerns


def _ownership_map() -> dict[str, list[str]]:
    rows = markdown_table_rows(read(GOV / "ownership-registry.md"))
    header = [h.lower() for h in rows[0]]
    id_i = header.index("concern_id")
    owner_i = header.index("owner")
    prod_i = header.index("production")
    mapping: dict[str, list[str]] = {}
    for row in rows[1:]:
        if len(row) <= max(id_i, owner_i, prod_i):
            continue
        cid = row[id_i]
        if row[prod_i].lower().startswith("no"):
            continue
        mapping.setdefault(cid, []).append(row[owner_i])
    return mapping


def test_each_card_required_concern_has_single_owner() -> None:
    cards = read(GOV / "capability-cards.md")
    required_blocks = re.findall(
        r"\*\*Required Concerns\*\*\s*\|\s*([^|]+)\|",
        cards,
        flags=re.IGNORECASE,
    )
    assert required_blocks, "No Required Concerns rows found in capability-cards.md"
    needed: set[str] = set()
    for block in required_blocks:
        needed.update(re.findall(r"`([a-z][a-z0-9_]*)`", block))

    owners = _ownership_map()
    missing = sorted(c for c in needed if c not in owners)
    assert not missing, f"Missing ownership rows for concerns: {missing}"

    multi = {c: o for c, o in owners.items() if c in needed and len(o) != 1}
    assert not multi, f"Concerns without exactly one owner row: {multi}"

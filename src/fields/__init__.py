"""Field pack packages: generic, legal, pharmacy, madrsty.

Pack configuration is primarily YAML + text. Optional Python helpers stay inside
the pack and are loaded by name (`fields.{domain}.{module}`) — not imported
from the shared answer path. Pharmacy uses `recommend_pack.py`. Madrsty uses
`scope.py` for grade/subject isolation before retrieval.
"""

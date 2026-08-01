from pathlib import Path

path = Path(r"d:\mini-rag\src\stores\vectordb\providers\pgvector\search.py")
text = path.read_text(encoding="utf-8")

old_vec = """    if field_value is not None:
        where_clause = (
            f"WHERE {PgVectorTableSchemeEnums.METADATA.value} ->> :fkey = :fval "
        )
        params = {"vector": vec_str, "fkey": field_key, "fval": field_value, "limit": safe_limit}
    else:
        where_clause = (
            f"WHERE COALESCE({PgVectorTableSchemeEnums.METADATA.value} ->> :fkey, '') <> '' "
        )
        params = {"vector": vec_str, "fkey": field_key, "limit": safe_limit}
"""

new_vec = """    meta = PgVectorTableSchemeEnums.METADATA.value
    if field_value is not None:
        where_clause = f"WHERE {meta} ->> :fkey = :fval "
        params = {"vector": vec_str, "fkey": field_key, "fval": field_value, "limit": safe_limit}
    else:
        # Match Excel column presence OR leaflet logical field_name / field_names.
        where_clause = (
            "WHERE ("
            f"{meta} ->> 'field_name' = :logical_field "
            f"OR COALESCE({meta} -> 'field_names', '[]'::jsonb) ? :logical_field "
            f"OR COALESCE({meta} ->> :fkey, '') <> ''"
            ") "
        )
        params = {
            "vector": vec_str,
            "fkey": field_key,
            "logical_field": field_key,
            "limit": safe_limit,
        }
"""

if old_vec not in text:
    raise SystemExit("vector field where missing")
text = text.replace(old_vec, new_vec, 1)

old_text = """    if field_value is not None:
        field_clause = f"{PgVectorTableSchemeEnums.METADATA.value} ->> :fkey = :fval"
        params = {
            "lang": language, "tsquery": tsquery_str, "fkey": field_key,
            "fval": field_value, "limit": safe_limit,
        }
    else:
        field_clause = (
"""

# Read a bit more context for text field else branch
idx = text.find(old_text)
if idx < 0:
    raise SystemExit("text field where missing")
# find the else field_clause assignment end
snippet = text[idx:idx+500]
print("FOUND TEXT SNIPPET:")
print(snippet)
path.write_text(text, encoding="utf-8")
print("vector part patched; inspect text part next")

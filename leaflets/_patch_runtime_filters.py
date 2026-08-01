from pathlib import Path

path = Path(r"d:\mini-rag\src\services\rag\skills\runtime_support.py")
text = path.read_text(encoding="utf-8")

old_import = "from services.rag.skills.context import SkillExecutionContext"
new_import = (
    "from services.rag.skills.context import SkillExecutionContext\n"
    "from services.rag.skills.filters import jsonb_metadata_filter, logical_field_key"
)
if "jsonb_metadata_filter" not in text:
    if old_import not in text:
        raise SystemExit("import anchor missing")
    text = text.replace(old_import, new_import, 1)

old_block = """    field_resolution = resolve_from_plan(
        query_plan,
        profile.field_registry,
        field_manifest,
    )
    field_is_list = bool(
        field_resolution is not None
        and getattr(field_resolution, "output_shape", "prose") == "list"
    )

    from core.field_resolution import resolve_entity_key

    entity_key = field_manifest.entity_key
    if not entity_key and field_manifest.columns:
        entity_key = resolve_entity_key(
            field_manifest,
            profile.field_registry,
            available_keys=set(field_manifest.columns.keys()),
        )

    entity_prefix = None
    if query_plan.entity:
        entity_prefix = str(query_plan.entity).strip().upper() or None

    entity_filter = dict(metadata_filter or {})
"""

new_block = """    field_resolution = resolve_from_plan(
        query_plan,
        profile.field_registry,
        field_manifest,
    )
    # Leaflet/txt corpora store logical fields in chunk metadata field_name,
    # not Excel column keys — fall back to Skill profile / plan field.
    if field_resolution is None or not getattr(field_resolution, "column_keys", ()):
        logical = logical_field_key(skill_ctx.metadata_filters) or (
            query_plan.field if query_plan.field and query_plan.field != "unknown" else None
        )
        if logical:
            from core.field_resolution import FieldResolution

            field_resolution = FieldResolution(
                concept=logical,
                column_keys=(logical,),
                output_shape=(
                    getattr(field_resolution, "output_shape", "prose")
                    if field_resolution is not None
                    else "prose"
                ),
                via="skill_profile_field",
            )
    field_is_list = bool(
        field_resolution is not None
        and getattr(field_resolution, "output_shape", "prose") == "list"
    )

    from core.field_resolution import resolve_entity_key

    entity_key = field_manifest.entity_key
    if not entity_key and field_manifest.columns:
        entity_key = resolve_entity_key(
            field_manifest,
            profile.field_registry,
            available_keys=set(field_manifest.columns.keys()),
        )
    # Leaflet chunks persist the brand under metadata key "entity".
    if not entity_key and query_plan.entity:
        entity_key = "entity"

    entity_prefix = None
    if query_plan.entity:
        entity_prefix = str(query_plan.entity).strip().upper() or None

    # Never apply Skill field/source lists as raw JSONB containment.
    entity_filter = dict(jsonb_metadata_filter(metadata_filter) or {})
"""

if old_block not in text:
    raise SystemExit("block anchor missing")
text = text.replace(old_block, new_block, 1)
path.write_text(text, encoding="utf-8")
print("patched", path)

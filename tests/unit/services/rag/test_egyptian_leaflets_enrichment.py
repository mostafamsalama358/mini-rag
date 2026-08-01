from pathlib import Path

from services.FieldRegistry import FieldRegistry
from services.rag.metadata_enrichment import enrich_chunk_metadata


def test_egyptian_leaflet_brand_and_inn_aliases():
    profile = FieldRegistry().load().build_profile("pharmacy")
    text = Path("leaflets/01_panadol_paracetamol_500.txt").read_text(encoding="utf-8")
    meta = enrich_chunk_metadata(
        {"file_name": "01_panadol_paracetamol_500.txt"},
        text,
        enrichment=profile.metadata,
    )
    assert meta.get("entity") == "Panadol"
    assert "paracetamol" in [a.lower() for a in (meta.get("entity_aliases") or [])]
    assert "warfarin" not in [a.lower() for a in (meta.get("entity_aliases") or [])]


def test_augmentin_does_not_inherit_amoxil_brand_alias():
    profile = FieldRegistry().load().build_profile("pharmacy")
    text = Path("leaflets/21_augmentin_1g.txt").read_text(encoding="utf-8")
    meta = enrich_chunk_metadata(
        {"file_name": "21_augmentin_1g.txt"},
        text,
        enrichment=profile.metadata,
    )
    assert meta.get("entity") == "Augmentin"
    aliases = [a.lower() for a in (meta.get("entity_aliases") or [])]
    assert "amoxicillin" in aliases
    assert "amoxil amoxicillin" not in aliases

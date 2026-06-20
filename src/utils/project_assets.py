import hashlib


def build_asset_fingerprint(assets) -> str:
    """Stable hash of project files; changes when files are added or removed."""
    if not assets:
        return "empty"

    parts = sorted(
        f"{asset.asset_id}:{asset.asset_name}"
        for asset in assets
    )
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest[:16]

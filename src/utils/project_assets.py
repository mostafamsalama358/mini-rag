import hashlib


def content_token_from_mapping(source: dict | None) -> str:
    """checksum:version from asset_config or chunk metadata.

    Accepts the canonical keys and the Egaabat camelCase aliases. An empty
    token means the upload did not declare a version.
    """
    if not isinstance(source, dict):
        return ":"
    checksum = source.get("checksum_sha256")
    if checksum in (None, ""):
        checksum = source.get("checksumSha256") or ""
    version = source.get("content_version")
    if version in (None, ""):
        version = source.get("contentVersion", "")
    checksum_text = "" if checksum in (None, "") else str(checksum).strip()
    version_text = "" if version in (None, "") else str(version).strip()
    return f"{checksum_text}:{version_text}"


def build_asset_fingerprint(assets) -> str:
    """Stable hash of project files.

    Changes when files are added, removed, or when asset_config carries a new
    checksum_sha256 / content_version so a replaced PDF is not skipped.
    """
    if not assets:
        return "empty"

    parts = sorted(
        f"{asset.asset_id}:{asset.asset_name}:{content_token_from_mapping(getattr(asset, 'asset_config', None))}"
        for asset in assets
    )
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest[:16]

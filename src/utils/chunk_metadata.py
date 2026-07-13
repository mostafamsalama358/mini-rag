def _humanize_file_name(file_name: str | None) -> str | None:
    if not file_name:
        return file_name

    name = str(file_name).replace("\\", "/").split("/")[-1]
    prefix, sep, remainder = name.partition("_")
    if sep and prefix.isalnum() and len(prefix) <= 16 and remainder:
        return remainder

    return name


def normalize_chunk_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if value is not None}


def format_source_label(
    metadata: dict | None,
    lang: str = "en",
    *,
    label_template: str | None = None,
) -> str:
    """Build a citation label from chunk metadata.

    When ``label_template`` is set (pack MetadataProfile), it is applied via
    ``str.format_map`` against the metadata dict (FR-015). Missing keys become
    empty strings. When unset, preserve the legacy ``file — page N`` format.
    """
    metadata = normalize_chunk_metadata(metadata)

    file_name = _humanize_file_name(metadata.get("file_name"))
    if not file_name and metadata.get("source"):
        source = str(metadata["source"])
        file_name = source.replace("\\", "/").split("/")[-1]

    if label_template:
        values = {key: ("" if value is None else value) for key, value in metadata.items()}
        values.setdefault("file_name", file_name or "")
        try:
            return str(label_template).format_map(_DefaultEmpty(values)).strip() or (
                str(file_name) if file_name else (
                    "مصدر غير معروف" if lang.lower().startswith("ar") else "unknown source"
                )
            )
        except Exception:
            pass

    page = metadata.get("page")
    if page is not None:
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = None

    page_label = "صفحة" if lang.lower().startswith("ar") else "page"

    if file_name and page:
        return f"{file_name} — {page_label} {page}"

    if file_name:
        return str(file_name)

    if page:
        return f"{page_label} {page}"

    return "مصدر غير معروف" if lang.lower().startswith("ar") else "unknown source"


class _DefaultEmpty(dict):
    def __missing__(self, key: str) -> str:
        return ""

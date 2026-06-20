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


def format_source_label(metadata: dict | None, lang: str = "en") -> str:
    metadata = normalize_chunk_metadata(metadata)

    file_name = _humanize_file_name(metadata.get("file_name"))
    if not file_name and metadata.get("source"):
        source = str(metadata["source"])
        file_name = source.replace("\\", "/").split("/")[-1]

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

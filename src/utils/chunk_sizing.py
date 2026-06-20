def resolve_chunk_params(
    text_length: int,
    base_chunk_size: int,
    base_overlap: int,
    *,
    min_chunk_size: int = 200,
    max_chunk_size: int = 1000,
) -> tuple[int, int]:
    """Scale chunk size relative to text length.

    Short texts use smaller chunks (fewer splits, tighter retrieval).
    Long texts use larger chunks (fewer embeddings, more context per chunk).
    """
    if text_length <= 0:
        return max(1, base_chunk_size), max(0, base_overlap)

    if text_length <= min_chunk_size:
        return text_length, 0

    if text_length <= 600:
        scale = 0.6
    elif text_length <= 1500:
        scale = 0.75
    elif text_length <= 4000:
        scale = 1.0
    elif text_length <= 12000:
        scale = 1.15
    else:
        scale = 1.3

    chunk_size = int(round(base_chunk_size * scale))
    chunk_size = max(min_chunk_size, min(max_chunk_size, chunk_size))

    if chunk_size >= text_length:
        return text_length, 0

    overlap_ratio = 0.15 if text_length <= 1500 else 0.18
    overlap = int(round(chunk_size * overlap_ratio))
    overlap = max(20, min(overlap, chunk_size // 3, int(base_overlap * scale)))

    return chunk_size, overlap

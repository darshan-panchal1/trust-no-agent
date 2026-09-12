"""Fixed-width chunking with optional overlap (FR-003, FR-004)."""

from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Split text into fixed-width character windows, optionally overlapping."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks

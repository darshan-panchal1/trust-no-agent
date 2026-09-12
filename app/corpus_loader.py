"""Corpus filesystem access — the only reader of `app/corpus/` (FR-008)."""

from __future__ import annotations

from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def list_documents() -> list[str]:
    """Filenames of every corpus document, sorted."""
    return sorted(p.name for p in CORPUS_DIR.glob("*.md"))


def read_document(filename: str) -> str:
    """Read one corpus document's content by filename."""
    path = CORPUS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"corpus document not found: {filename}")
    return path.read_text()

"""Deterministic plausibility checks (FR-028's non-judged half). Not collected by pytest."""

from __future__ import annotations

import re

MIN_LENGTH = 5  # catches empty/whitespace-only and single-character garbage, not terseness
MAX_LENGTH = 4700  # 1.5x the longest real cached answer (3131 chars), rounded to the nearest 100
_TRAILING_CLOSERS = ")]}\"'"
_DOC_EXTENSIONS = (".md", ".pdf", ".txt")
_SOURCE_LINE = re.compile(r"^source:\s*\S+$", re.IGNORECASE)

# Actual error-shaped tokens, not loose English words ("none" is ordinary prose, not an error).
_ERROR_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\btraceback\b",
        r"\berror:",
        r"\bexception\b",
        r"\bundefined\b",
        r"\bnull\b",
        r'file "[^"]*", line \d+',  # Python stack-frame marker
    )
)


def has_reasonable_length(text: str) -> bool:
    """Not a fluency proxy — a correct, terse answer like "$500." must pass. Only
    rejects degenerate output: empty/whitespace strips to 0 chars, under MIN_LENGTH."""
    return MIN_LENGTH <= len(text.strip()) <= MAX_LENGTH


def _ends_in_citation(text: str) -> bool:
    """`Source: <file>`, or a bare line ending `.md`/`.pdf`/`.txt` — real, correctly
    formatted output the punctuation check alone can't see past."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    last = lines[-1] if lines else ""
    return last.lower().endswith(_DOC_EXTENSIONS) or bool(_SOURCE_LINE.match(last))


def ends_in_complete_sentence(text: str) -> bool:
    """Strips trailing closers (`)]}"'`) first: `"...material.)"` ends on the `.`."""
    trimmed = text.rstrip().rstrip(_TRAILING_CLOSERS)
    return trimmed.endswith((".", "!", "?")) or _ends_in_citation(text)


def has_no_error_strings(text: str) -> bool:
    return not any(pattern.search(text) for pattern in _ERROR_PATTERNS)


def is_non_empty(text: str) -> bool:
    return len(text.strip()) > 0


def assert_deterministic_vibes(text: str) -> None:
    assert has_reasonable_length(text), f"length out of band: {len(text)} chars"
    assert ends_in_complete_sentence(text), "does not end in a complete sentence"
    assert has_no_error_strings(text), "contains an error-shaped string"
    assert is_non_empty(text), "empty answer"

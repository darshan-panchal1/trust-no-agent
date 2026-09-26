"""v1.1.0 guard (spec FR-028/029, SC-002): the evidence store v1.0.0 committed is still read
and written byte-for-byte, and the key derivation has not moved. Written before `store.py`
changed, green from the first run — a regression guard, not a TDD red test."""

from __future__ import annotations

from evals.cache.keys import make_key
from evals.cache.store import CACHE_DIR, CacheEntry

V1_ENTRY_FLOOR = 1120  # entries committed at v1.0.0; a refresh may add, never lose
# make_key("ragas:faithfulness", "m", "p"), computed on the v1.0.0 code, 2026-09-26.
GOLDEN_KEY = "8f166112f94539af8025dd928301618e680428195a66ed31207493f1ae190d49"


def test_every_committed_entry_round_trips_byte_identically() -> None:
    """A new optional field must not change what an old entry serialises to — otherwise
    every old-path write after v1.1.0 would silently differ from the committed file."""
    files = sorted(CACHE_DIR.glob("*.json"))
    assert len(files) >= V1_ENTRY_FLOOR
    drifted = [
        path.name
        for path in files
        if CacheEntry.model_validate_json(text := path.read_text()).model_dump_json() != text
    ]
    assert drifted == []


def test_the_cache_key_derivation_is_unchanged() -> None:
    assert make_key("ragas:faithfulness", "m", "p") == GOLDEN_KEY

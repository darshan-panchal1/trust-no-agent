"""The one door: `read_or_raise` (offline, cannot write) and `read_or_call` (the only
write-capable path). Article III — one JSON file per key."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from evals import cost

CACHE_DIR = Path(__file__).resolve().parent.parent / ".judge_cache"

REFRESH_COMMAND = "uv run python -m evals.cli record"  # FR-031: real, and runnable


class CacheEntry(BaseModel):
    """One call's evidence (FR-030). `call_kind` makes each file self-describing and is
    what Article VIII's per-metric table groups by."""

    call_kind: str
    response: str
    input_tokens: int
    output_tokens: int
    usd: float | None  # None: no dated price for this call's model (Article VIII)


class CacheMiss(RuntimeError):
    """Raised by `read_or_raise` on a miss. Names the key; never falls through to a call."""


def _record(entry: CacheEntry, cached: bool) -> CacheEntry:
    # Every served call lands in Article VIII's table, hit or miss.
    cost.record_call(entry.call_kind, entry.input_tokens, entry.output_tokens, entry.usd, cached)
    return entry


def read_or_raise(key: str) -> CacheEntry:
    """Pure offline reader. No call function accepted — nothing here can write."""
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        raise CacheMiss(
            f"cache miss for key {key!r} — no {path} is committed. "
            f"Create it with `{REFRESH_COMMAND}`; never as a side effect of a test run."
        )
    return _record(CacheEntry.model_validate_json(path.read_text()), cached=True)


def read_or_call(key: str, call_fn: Callable[[], CacheEntry]) -> CacheEntry:
    """The only write-capable path. On a miss, invokes `call_fn` once and persists it."""
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return _record(CacheEntry.model_validate_json(path.read_text()), cached=True)
    entry = call_fn()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(entry.model_dump_json())
    return _record(entry, cached=False)

"""The one door: `read_or_raise` (offline, cannot write) and `read_or_call` (the only
write-capable path). Article III — one JSON file per key."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

from evals import cost
from evals.cache import judging, location

CACHE_DIR = Path(__file__).resolve().parent.parent / ".judge_cache"
REFRESH_COMMAND = "uv run python -m evals.cli record"  # FR-031: real, and runnable


class CacheEntry(BaseModel):
    """One call's evidence (FR-030); `call_kind` self-describes it for Article VIII's table.
    `fingerprint` (v1.1) sits beside the key, never in it; omitted when None, v1 bytes hold."""

    call_kind: str
    response: str
    input_tokens: int
    output_tokens: int
    usd: float | None  # None: no dated price for this call's model (Article VIII)
    fingerprint: str | None = Field(default=None, exclude_if=lambda v: v is None)


class CacheMiss(RuntimeError):
    """Raised by `read_or_raise` on a miss. Names the key; never falls through to a call."""


def _record(entry: CacheEntry, cached: bool) -> CacheEntry:
    # Every served call lands in Article VIII's table, hit or miss.
    cost.record_call(entry.call_kind, entry.input_tokens, entry.output_tokens, entry.usd, cached)
    return entry


def read_or_raise(key: str) -> CacheEntry:
    """Pure offline reader. No call function accepted — nothing here can write."""
    path = (location.current() or CACHE_DIR) / f"{key}.json"
    if not path.exists():
        raise CacheMiss(
            f"cache miss for key {key!r} — no {path} is committed. "
            f"Create it with `{REFRESH_COMMAND}`; never as a side effect of a test run."
        )
    entry = CacheEntry.model_validate_json(path.read_text())
    return _record(judging.observe(key, entry), cached=True)


def read_or_call(key: str, call_fn: Callable[[], CacheEntry]) -> CacheEntry:
    """The only write-capable path. On a miss, invokes `call_fn` once and persists it."""
    path = (location.current() or CACHE_DIR) / f"{key}.json"
    if path.exists():
        return read_or_raise(key)
    entry = judging.stamp(call_fn())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(entry.model_dump_json())
    return _record(judging.observe(key, entry), cached=False)

"""The store's two session hooks (research R2, R4). `observe` runs on every entry served,
`stamp` on every entry about to be written. Each is a passthrough unless a judging session is
active and the entry is that session's judge kind — `ragas:embeddings` and `generate:*`
entries are never fingerprinted and never paired with usage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from evals.cache.session import FingerprintMismatch, active

if TYPE_CHECKING:
    from evals.cache.store import CacheEntry


def observe(key: str, entry: CacheEntry) -> CacheEntry:
    """Refuse a stored fingerprint that disagrees; otherwise record the entry as served."""
    current = active()
    if current is None or entry.call_kind != current.judge_call_kind:
        return entry
    if entry.fingerprint is not None and entry.fingerprint != current.fingerprint:
        raise FingerprintMismatch(key, entry.fingerprint, current.fingerprint, entry.response)
    current.served[key] = entry
    return entry


def stamp(entry: CacheEntry) -> CacheEntry:
    """Attach the config fingerprint, and the next queued real usage if there is one."""
    current = active()
    if current is None or entry.call_kind != current.judge_call_kind:
        return entry
    update: dict[str, object] = {"fingerprint": current.fingerprint}
    if current.pending_usage:
        update["input_tokens"], update["output_tokens"] = current.pending_usage.popleft()
    return entry.model_copy(update=update)

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
    """Attach the config fingerprint and the real usage queued since the last write. Calls are
    sequential, so everything queued belongs to this entry — including an attempt instructor
    retried after a malformed reply, which the provider billed and which is summed in here."""
    current = active()
    if current is None or entry.call_kind != current.judge_call_kind:
        return entry
    update: dict[str, object] = {"fingerprint": current.fingerprint}
    if current.pending_usage:
        update["input_tokens"] = sum(prompt for prompt, _ in current.pending_usage)
        update["output_tokens"] = sum(completion for _, completion in current.pending_usage)
        current.pending_usage.clear()
    return entry.model_copy(update=update)

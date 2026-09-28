"""The judging session (research R2, R4, R5): state for one per-record evaluation, read by
`evals/cache/judging.py` at the store's one door. With no session active, nothing here or
there changes what the store reads or writes — the v1 path is untouched."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evals.cache.store import CacheEntry


class FingerprintMismatch(RuntimeError):
    def __init__(self, key: str, stored: str, expected: str, response: str) -> None:
        super().__init__(f"stored fingerprint {stored} != current {expected} for {key}")
        self.key, self.stored, self.expected, self.response = key, stored, expected, response


@dataclass
class Session:
    fingerprint: str
    judge_call_kind: str  # the only kind fingerprinted and paired with usage
    pending_usage: deque[tuple[int, int]] = field(default_factory=deque)
    served: dict[str, CacheEntry] = field(default_factory=dict)


_active: Session | None = None


@contextmanager
def begin(fingerprint: str, judge_call_kind: str) -> Iterator[Session]:
    global _active
    if _active is not None:
        raise RuntimeError("judging sessions do not nest")
    _active = Session(fingerprint, judge_call_kind)
    try:
        yield _active
    finally:
        _active = None


def push_usage(response: object, *_args: object, **_kwargs: object) -> None:
    """An instructor `completion:response` hook: queue one call's usage for its write."""
    usage = getattr(response, "usage", None)
    if _active is not None and usage is not None:
        _active.pending_usage.append((usage.prompt_tokens, usage.completion_tokens))



def active() -> Session | None:
    return _active

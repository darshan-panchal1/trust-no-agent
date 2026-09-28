"""Which directory the evidence store reads and writes (research R1, R13). An override is set
for one per-record call and always restored; with none set, `store.CACHE_DIR` is used, exactly
as in v1.0.0. Imports nothing from `store`, which reads this at call time."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_override: Path | None = None


def current() -> Path | None:
    return _override


@contextmanager
def override(path: Path) -> Iterator[None]:
    """Synchronous code only (Article X), so one process-level slot cannot interleave."""
    global _override
    previous, _override = _override, path
    try:
        yield
    finally:
        _override = previous


def default_cache_dir(committed: Path) -> Path | None:
    """The committed store, but only inside a repo checkout. An installed wheel ships the
    store inside site-packages, which has no `.git` — so it never silently writes a caller's
    records into itself (spec FR-032). A worktree's `.git` is a file; `exists()` accepts it."""
    root = committed.parents[1]
    in_checkout = (root / ".git").exists() and (root / "pyproject.toml").is_file()
    return committed if in_checkout else None

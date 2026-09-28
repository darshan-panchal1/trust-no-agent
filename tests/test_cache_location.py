"""T008: the caller's cache directory (research R1, R13) — reached through the unchanged
`read_or_raise(key)` signature, restored after every call, and defaulted to the committed
store only inside a repo checkout."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.cache import location, store
from evals.cache.store import CacheEntry, CacheMiss

pytestmark = pytest.mark.usefixtures("isolated_cache")


def _entry(response: str) -> str:
    return CacheEntry(
        call_kind="ragas:x", response=response, input_tokens=1, output_tokens=1, usd=0.0
    ).model_dump_json()


def test_the_committed_store_is_the_default_inside_a_checkout() -> None:
    committed = Path(location.__file__).resolve().parent.parent / ".judge_cache"
    assert location.default_cache_dir(committed) == committed


def test_there_is_no_default_outside_a_checkout(tmp_path: Path) -> None:
    assert location.default_cache_dir(tmp_path / "evals" / ".judge_cache") is None


def test_an_override_redirects_reads_and_names_its_own_path_on_a_miss(tmp_path: Path) -> None:
    (tmp_path / "abc.json").write_text(_entry("from override"))
    with location.override(tmp_path):
        assert store.read_or_raise("abc").response == "from override"
        with pytest.raises(CacheMiss, match=str(tmp_path)):
            store.read_or_raise("missing")
    with pytest.raises(CacheMiss):
        store.read_or_raise("abc")  # back on the default store, which never had it


def test_the_override_is_restored_even_when_the_block_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError), location.override(tmp_path):
        raise ValueError("boom")
    assert location.current() is None

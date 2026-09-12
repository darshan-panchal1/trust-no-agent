"""Fixtures shared by the `tests/` package. One level deep, per Article VII.

Opt in with `pytestmark = pytest.mark.usefixtures("isolated_cache")` — deliberately not
autouse, because `test_vibes.py` must read the real committed evidence, and an autouse
isolation fixture would silently turn its assertions into permanent skips.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from evals import cost
from evals.cache import store


@pytest.fixture
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """A throwaway evidence store, with cost accounting cleared on both sides.

    Without the reset, a test writing one stub entry would appear in Article VIII's
    end-of-run table as a call the suite really made — a cost table that lies about a
    run is the same class of defect this repository exists to expose.
    """
    monkeypatch.setattr(store, "CACHE_DIR", tmp_path / ".judge_cache")
    cost.reset()
    yield
    cost.reset()

"""v1.1.0 guard (spec FR-036/037, SC-003): `RunSummary`'s shape is frozen, and the offline
summary `EvalSuite.run()` builds is served entirely from committed evidence. Unlike the
fixtures that skip on a miss, a miss here fails — a skip would hide exactly the regression
this module exists to catch."""

from __future__ import annotations

import json

import pytest

from evals import cost
from evals.ops.run_summary import RunSummary
from evals.ops.summary import build_summary
from tests.repo_files import REPO_ROOT

SNAPSHOT = REPO_ROOT / "tests" / "snapshots" / "run_summary_schema.json"


def test_run_summary_schema_matches_the_v1_snapshot() -> None:
    current = json.dumps(RunSummary.model_json_schema(), indent=2, sort_keys=True) + "\n"
    assert current == SNAPSHOT.read_text()


def _counts() -> dict[str, tuple[int, int]]:
    return {row.call_kind: (row.calls, row.cached) for row in cost.rows()}


@pytest.mark.usefixtures("socket_disabled")
def test_offline_summary_is_built_entirely_from_committed_evidence() -> None:
    """Measured as a before/after delta, never by resetting: a reset here would erase every
    earlier test's rows from Article VIII's end-of-run table."""
    before = _counts()
    assert build_summary().metrics
    after = _counts()
    served = {kind: (calls - before.get(kind, (0, 0))[0], cached - before.get(kind, (0, 0))[1])
              for kind, (calls, cached) in after.items()}
    assert any(calls for calls, _ in served.values())
    assert [kind for kind, (calls, cached) in served.items() if calls != cached] == []

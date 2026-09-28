"""T057's offline guard: the hand-run live pass refuses to start without a key, and its fixed
records and rubric are valid contract values. It is never *run* here — it makes real NIM
calls, which the default suite must not (Article VI)."""

from __future__ import annotations

import pytest

from trustnoagent import list_evaluators, live_check


def test_it_refuses_to_start_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="NVIDIA_API_KEY"):
        live_check.main()


def test_its_records_satisfy_every_evaluator_it_runs() -> None:
    needs = set().union(*(info.requires for info in list_evaluators(live_check.RUBRIC)))
    for record in live_check.RECORDS.values():
        assert all(record.present(field) for field in needs)

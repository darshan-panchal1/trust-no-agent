"""T031 (US2): an unknown evaluator id is a result naming it, never a `KeyError` — and it is
answered before any judge configuration is read (spec FR-004, transition 1 of the data model)."""

from __future__ import annotations

import pytest

from evals.contract import EvalRecord
from trustnoagent import evaluate

RECORD = EvalRecord(input="q", output="a")


@pytest.mark.usefixtures("socket_disabled")
def test_an_unknown_id_is_a_result_that_names_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """With every env var unset, a `from_env()` call would raise naming JUDGE_MODEL. The
    unknown-id answer must come first: it is the real problem, and the first one to fix."""
    for name in ("JUDGE_MODEL", "GENERATOR_MODEL", "NVIDIA_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    result = evaluate("tna.ragas.nope", RECORD)
    assert result.status == "error"
    assert (result.evaluator_id, result.evaluator_version) == ("tna.ragas.nope", "")
    assert result.error is not None and "tna.ragas.nope" in result.error
    assert "tna.ragas.faithfulness" in result.error  # lists what would have worked
    assert (result.score, result.label, result.judge_fingerprint) == (None, None, None)


@pytest.mark.parametrize("bad", ["", "faithfulness", "TNA.RAGAS.FAITHFULNESS", "tna.ragas."])
def test_near_misses_are_unknown_too_not_silently_matched(bad: str) -> None:
    result = evaluate(bad, RECORD)
    assert (result.status, result.evaluator_id) == ("error", bad)


def test_a_non_string_id_is_still_a_programming_error() -> None:
    with pytest.raises(TypeError, match="evaluator"):
        evaluate(123, RECORD)  # type: ignore[arg-type]

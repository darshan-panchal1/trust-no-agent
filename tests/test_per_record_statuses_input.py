"""T034 (US3, FR-004/014/015/017): failures that come from the record, the configuration or the
evidence store are statuses on the result — with no score, no exception, and no judge call."""

from __future__ import annotations

import pytest

from evals import cost
from evals.cache import location
from evals.contract import EvalRecord, EvalResult
from trustnoagent import evaluate

NOVEL = EvalRecord(input="a question no one recorded", output="an answer", contexts=("c",))


def _no_verdict(result: EvalResult) -> None:
    assert result.status != "ok"
    assert (result.score, result.label) == (None, None)


def _served() -> dict[str, int]:
    return {row.call_kind: row.calls for row in cost.rows()}


@pytest.mark.usefixtures("socket_disabled")
def test_a_missing_required_field_is_skipped_and_makes_no_judge_call() -> None:
    before = _served()
    result = evaluate("tna.ragas.faithfulness", EvalRecord(input="q", output="a"))
    _no_verdict(result)
    assert result.status == "skipped" and result.error is not None and "contexts" in result.error
    assert _served() == before


@pytest.mark.usefixtures("socket_disabled")
def test_an_empty_field_is_present_so_it_is_scored_not_skipped() -> None:
    result = evaluate("tna.ragas.faithfulness", EvalRecord(input="q", output="a", contexts=()))
    assert result.status != "skipped"  # here it is a cache miss instead: it was really tried


def test_a_bare_rubric_id_explains_that_rubrics_are_passed_as_definitions() -> None:
    result = evaluate("tna.judge.tone", NOVEL)
    _no_verdict(result)
    assert result.error is not None and "definition" in result.error


def test_an_unset_judge_model_is_an_error_naming_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUDGE_MODEL")
    result = evaluate("tna.ragas.faithfulness", NOVEL)
    _no_verdict(result)
    assert result.error is not None and "JUDGE_MODEL" in result.error


def test_no_cache_directory_outside_a_checkout_is_an_error_asking_for_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(location, "default_cache_dir", lambda committed: None)
    result = evaluate("tna.ragas.faithfulness", NOVEL)
    _no_verdict(result)
    assert result.error is not None and "cache_dir" in result.error

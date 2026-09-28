"""T035, Ragas side (US3, FR-016): an unusable judge reply is `invalid_output` with its text
kept; a failure before any reply is `error`. Exceptions: `tests/per_record_ragas_failures.py`."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from evals.component import record_eval
from tests.per_record_ragas_failures import BAD_REPLIES, JUDGE_TEXT, retry, score_with
from tests.per_record_support import golden_record
from trustnoagent import evaluate

RECORD = golden_record("v2_fixed", 0)[1]


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("case", sorted(BAD_REPLIES))
def test_an_unusable_judge_reply_is_invalid_output_with_no_verdict(
    case: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    score_with(monkeypatch, BAD_REPLIES[case])
    result = evaluate("tna.ragas.faithfulness", RECORD)
    assert result.status == "invalid_output"
    assert (result.score, result.label) == (None, None)
    assert result.judge_fingerprint is not None
    if case in ("bad_reply", "truncated"):
        assert result.raw["responses"] == [JUDGE_TEXT]  # the judge's own text, kept


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize(
    ("produce", "expected"),
    [
        (lambda: retry(None), "InstructorRetryException"),
        (lambda: RuntimeError("boom"), "RuntimeError: boom"),
    ],
    ids=["provider_failure_before_any_reply", "any_other_exception"],
)
def test_a_failure_with_no_judge_reply_is_error_not_invalid_output(
    produce: Callable[[], object], expected: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    score_with(monkeypatch, produce)
    result = evaluate("tna.ragas.faithfulness", RECORD)
    assert result.status == "error" and result.error is not None and expected in result.error
    assert (result.score, result.label) == (None, None)


@pytest.mark.usefixtures("socket_disabled")
def test_missing_local_embeddings_name_the_optional_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_embeddings(_name: str, _mode: str) -> object:
        raise ImportError("No module named 'sentence_transformers'")

    monkeypatch.setattr(record_eval, "build_metric", no_embeddings)
    result = evaluate("tna.ragas.response_relevancy", RECORD)
    assert result.status == "error" and result.error is not None
    assert "uv sync --group calibration" in result.error and result.score is None

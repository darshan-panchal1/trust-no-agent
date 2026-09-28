"""T037's discriminator, isolated: a bare `KeyError` or `ValueError` from GEval is malformed
judge output only when a reply was obtained. With none, it is an ordinary bug and must surface
as `error` — otherwise every programming mistake would masquerade as a judge failure."""

from __future__ import annotations

import json

import pytest

from evals.behavior import record_eval
from tests.per_record_support import golden_record
from trustnoagent import evaluate

ID = "tna.deepeval.refusal_correctness"
RECORD = golden_record("v2_fixed", 0)[1]
GEVAL_MESSAGE = "Evaluation LLM outputted an invalid JSON. Please use a better evaluation model."


def _measure_raises(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    def measure(_metric: object, _record: object) -> tuple[None, None]:
        raise exc

    monkeypatch.setattr(record_eval, "_measure", measure)


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("exc", [KeyError("score"), ValueError("bad"), TypeError("bug")])
def test_a_bare_exception_with_no_judge_reply_is_an_error_not_invalid_output(
    exc: Exception, monkeypatch: pytest.MonkeyPatch
) -> None:
    _measure_raises(monkeypatch, exc)
    result = evaluate(ID, RECORD)
    assert result.status == "error" and (result.score, result.label) == (None, None)


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize(
    ("exc", "kept"),
    [
        (ValueError(GEVAL_MESSAGE), GEVAL_MESSAGE),  # GEval's own message needs no served entry
        (json.JSONDecodeError("Expecting value", "not json", 0), "not json"),  # `doc` is the text
    ],
    ids=["geval_invalid_json_message", "json_decode_error"],
)
def test_geval_own_malformed_output_signals_are_invalid_output(
    exc: Exception, kept: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _measure_raises(monkeypatch, exc)
    result = evaluate(ID, RECORD)
    assert result.status == "invalid_output" and result.raw["responses"] == [kept]

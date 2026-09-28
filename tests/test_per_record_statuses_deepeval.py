"""T035, DeepEval side (US3, FR-016), end to end through a socket-free NIM. GEval never validates
what the judge returns, so malformed output escapes it as three different exceptions: a
`JSONDecodeError` (text that is not JSON), a bare `KeyError` (JSON of the wrong shape) or a
`ValueError` (a score that is not a number). All are `invalid_output` with the judge's own text
kept; an HTTP failure, where no reply ever arrived, stays `error`."""

from __future__ import annotations

import httpx
import pytest

from evals.cache import store
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from tests.per_record_nim import MockNim, install
from trustnoagent import evaluate

RECORD = EvalRecord(input="Can I expense a gym?", output="Yes.", expected="No: out of scope")
LIVE = JudgeConfig("judge/m", "gen/m", mode="live", api_key="nvapi-test")
pytestmark = pytest.mark.usefixtures("socket_disabled", "isolated_cache")


def _score(monkeypatch: pytest.MonkeyPatch, handler: object) -> EvalResult:
    install(monkeypatch, MockNim(handler))  # type: ignore[arg-type]
    return evaluate("tna.deepeval.refusal_correctness", RECORD, LIVE, cache_dir=store.CACHE_DIR)


def _chat(content: str) -> object:
    body = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}
    return lambda _request: httpx.Response(200, json=body)


@pytest.mark.parametrize(
    "text", ["I think it is fine", "", '{"foo": 1}', '{"score": "high", "reason": "x"}']
)
def test_malformed_judge_output_is_invalid_output_with_the_text_kept(
    text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _score(monkeypatch, _chat(text))
    assert result.status == "invalid_output"
    assert (result.score, result.label) == (None, None)
    assert result.raw["responses"] == [text]


def test_a_provider_failure_with_no_reply_is_error_not_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _score(monkeypatch, lambda _request: httpx.Response(400, json={"error": "bad"}))
    assert result.status == "error" and result.error is not None
    assert "BadRequestError" in result.error and result.score is None


def test_the_control_a_well_formed_reply_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _score(monkeypatch, _chat('{"reason": "ok", "score": 10}'))
    assert (result.status, result.score) == ("ok", 1.0)
    assert (result.tokens_in, result.tokens_out) == (5, 2)

"""T041, live half (US4): a rubric call through a socket-free NIM. A judge that never returns
JSON is `invalid_output` with its text kept and nothing cached; a good reply is cached with real
tokens and its fingerprint. The key is carried by the config alone — US5's `judge_env`."""

from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from evals.cache import store
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from tests.per_record_nim import MockNim, install
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
POLITE = RubricJudge(
    "polite", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)
RECORD = EvalRecord(output="Happy to help.")


def _chat(content: str) -> MockNim:
    body = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 9, "total_tokens": 39}}
    return MockNim(lambda _request: httpx.Response(200, json=body))


def _live(monkeypatch: pytest.MonkeyPatch, mock: MockNim) -> EvalResult:
    install(monkeypatch, mock)  # the key travels in the config alone (US5), never via setenv
    live = replace(JudgeConfig.from_env(mode="live"), api_key="nvapi-test")
    return evaluate(POLITE, RECORD, live, cache_dir=store.CACHE_DIR)


def test_a_judge_that_never_returns_json_is_invalid_output_and_caches_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = _chat("Sure! The answer seems polite to me.")
    result = _live(monkeypatch, mock)
    assert (result.status, result.label) == ("invalid_output", None)
    assert result.raw["responses"] == ["Sure! The answer seems polite to me."]
    assert mock.calls == 2  # json_completion's one retry, then give up
    assert list(store.CACHE_DIR.glob("*.json")) == []


def test_a_good_live_reply_is_cached_with_real_tokens_and_its_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = _chat('{"label": "pass", "reason": "courteous"}')
    first = _live(monkeypatch, mock)
    assert (first.status, first.label, first.tokens_in, first.tokens_out) == ("ok", "pass", 30, 9)
    [written] = store.CACHE_DIR.glob("*.json")
    assert store.CacheEntry.model_validate_json(written.read_text()).fingerprint is not None
    assert _live(monkeypatch, mock) == first and mock.calls == 1  # second call: from evidence

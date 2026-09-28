"""Regression for the FR-033 gap T057 found live: a rubric reply that is valid JSON but breaks
the rubric's schema still gets cached with real usage before validation runs — that usage must
land on the `invalid_output` result, not `None` (evals/outcomes.py `invalid()`, spec 001, US7)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from evals.cache import store
from evals.contract import EvalRecord
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from tests.per_record_nim import MockNim, chat, install
from trustnoagent import evaluate

pytestmark = pytest.mark.usefixtures("isolated_cache", "socket_disabled")
DEPTH = RubricJudge("depth", "Rate 1-5.", frozenset({"output"}), score_range=(1, 5))
RECORD = EvalRecord(output="Thorough and well-cited.")


def test_invalid_output_carries_the_tokens_its_own_call_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, MockNim(chat("{}")))  # valid JSON, wrong shape — as T057 hit live
    live = replace(JudgeConfig.from_env(mode="live"), api_key="nvapi-test")
    result = evaluate(DEPTH, RECORD, live, cache_dir=store.CACHE_DIR)
    assert result.status == "invalid_output"
    assert (result.tokens_in, result.tokens_out) == (5, 2)  # per_record_nim.chat's fixed usage
    [written] = store.CACHE_DIR.glob("*.json")
    entry = store.CacheEntry.model_validate_json(written.read_text())
    assert (entry.input_tokens, entry.output_tokens) == (5, 2)  # the entry it came from

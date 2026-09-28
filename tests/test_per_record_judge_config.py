"""T047 (US5, FR-018/024): a `JudgeConfig` governs the call — its model, not `JUDGE_MODEL`,
drives every evidence key; live use with no key is an `error` naming it, before any client."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

import app.generate
import evals.judge.cached
import evals.ragas_llm
from evals.contract import EvalRecord
from evals.judge_config import JudgeConfig
from tests.per_record_support import golden_record
from trustnoagent import evaluate, list_evaluators

OTHER = JudgeConfig(judge_model="other/model", generator_model="other/gen")
RECORD = golden_record("v2_fixed", 1)[1]  # committed evidence exists — under the env's model


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("ident", [info.id for info in list_evaluators()])
def test_a_hand_built_model_moves_the_key_for_every_built_in(ident: str) -> None:
    under_env = evaluate(ident, RECORD)
    under_other = evaluate(ident, RECORD, OTHER)
    assert under_env.status == "ok"
    assert under_other.status == "error" and "cache miss for key" in (under_other.error or "")
    missed_key = (under_other.error or "").split("'")[1]
    assert missed_key not in str(under_env.raw["cache_keys"])  # a different key, not a lost file


@pytest.mark.usefixtures("socket_disabled")
def test_live_with_no_key_is_an_error_naming_it_and_builds_no_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[object] = []
    shim = SimpleNamespace(OpenAI=lambda **kwargs: built.append(kwargs))
    for module in (evals.ragas_llm, evals.judge.cached, app.generate):
        monkeypatch.setattr(module, "openai", shim)
    novel = EvalRecord(input="q?", output="a.", contexts=("c",), expected="e")
    for ident in [info.id for info in list_evaluators()]:
        result = evaluate(ident, novel, JudgeConfig.from_env(mode="live"))
        assert result.status == "error" and result.score is None, ident
        assert "NVIDIA_API_KEY" in (result.error or "") and "KeyError" not in (result.error or "")
    assert built == []


def test_a_missing_field_is_skipped_before_the_missing_key_is_reported() -> None:
    live = JudgeConfig.from_env(mode="live")
    result = evaluate("tna.ragas.faithfulness", EvalRecord(input="q", output="a"), live)
    assert result.status == "skipped" and "contexts" in (result.error or "")


def test_the_environment_is_exactly_as_it_was_after_a_call() -> None:
    before = {k: os.environ.get(k) for k in ("JUDGE_MODEL", "GENERATOR_MODEL", "NVIDIA_API_KEY")}
    evaluate("tna.ragas.faithfulness", RECORD, OTHER)
    after = {k: os.environ.get(k) for k in ("JUDGE_MODEL", "GENERATOR_MODEL", "NVIDIA_API_KEY")}
    assert after == before and before["NVIDIA_API_KEY"] is None

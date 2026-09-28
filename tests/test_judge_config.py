"""T006: `JudgeConfig.from_env()` — the two required accessors, the key only in live mode,
and a base URL that no environment variable can move (Article VI.a, spec FR-024/025)."""

from __future__ import annotations

import os

import pytest

from evals.judge_config import JudgeConfig
from evals.models import NIM_BASE_URL


def test_from_env_reads_both_models_and_defaults_to_offline() -> None:
    config = JudgeConfig.from_env()
    assert config.judge_model == os.environ["JUDGE_MODEL"]
    assert config.generator_model == os.environ["GENERATOR_MODEL"]
    assert (config.mode, config.api_key) == ("offline", None)


@pytest.mark.parametrize("name", ["JUDGE_MODEL", "GENERATOR_MODEL"])
def test_a_missing_model_raises_the_existing_error_naming_it(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(name)
    with pytest.raises(RuntimeError, match=name):
        JudgeConfig.from_env()


def test_the_key_is_read_only_in_live_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    assert JudgeConfig.from_env().api_key is None
    assert JudgeConfig.from_env(mode="live").api_key == "nvapi-test"


def test_a_missing_key_in_live_mode_is_not_an_error_here() -> None:
    """FR-018: the evaluator reports it as a status on use; building the config never raises."""
    assert JudgeConfig.from_env(mode="live").api_key is None


def test_no_environment_variable_can_move_the_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIM_BASE_URL", "http://evil.invalid/v1")
    assert JudgeConfig.from_env().base_url == NIM_BASE_URL


def test_the_key_never_appears_in_repr() -> None:
    config = JudgeConfig(judge_model="j", generator_model="g", api_key="nvapi-secret")
    assert "nvapi-secret" not in repr(config)

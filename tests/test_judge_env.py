"""T047/T048 (US5): `judge_env` exports a config for exactly one call and restores every variable
to its prior state — including absent — on normal exit and on an exception. The key never
outlives the call, so `test_provider_credentials.py`'s absence assertion keeps holding."""

from __future__ import annotations

import os

import pytest

from evals.judge_config import JudgeConfig
from trustnoagent.env import judge_env

NAMES = ("JUDGE_MODEL", "GENERATOR_MODEL", "NVIDIA_API_KEY")
LIVE = JudgeConfig("cfg/judge", "cfg/gen", mode="live", api_key="nvapi-from-config")


def _snapshot() -> dict[str, str | None]:
    return {name: os.environ.get(name) for name in NAMES}


def test_the_config_is_visible_inside_and_gone_after(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    before = _snapshot()
    with judge_env(LIVE):
        assert _snapshot() == {"JUDGE_MODEL": "cfg/judge", "GENERATOR_MODEL": "cfg/gen",
                               "NVIDIA_API_KEY": "nvapi-from-config"}
    assert _snapshot() == before and before["NVIDIA_API_KEY"] is None


def test_restored_after_an_exception_too() -> None:
    before = _snapshot()
    with pytest.raises(RuntimeError), judge_env(LIVE):
        raise RuntimeError("boom")
    assert _snapshot() == before


def test_an_offline_config_leaves_the_key_variable_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline never builds a client, so a key already in the environment is not its business."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-already-there")
    with judge_env(JudgeConfig("cfg/judge", "cfg/gen")):
        assert os.environ["NVIDIA_API_KEY"] == "nvapi-already-there"
        assert os.environ["JUDGE_MODEL"] == "cfg/judge"
    assert os.environ["NVIDIA_API_KEY"] == "nvapi-already-there"

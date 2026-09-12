"""Article III: `judge_model()`/`generator_model()` never default — a missing variable is
a hard error naming itself, the same discipline Article V applies to thresholds.
"""

from __future__ import annotations

import pytest

from evals.models import generator_model, judge_model


def test_judge_model_reads_the_env_var() -> None:
    assert judge_model() == "nvidia/nemotron-3-super-120b-a12b"


def test_generator_model_reads_the_env_var() -> None:
    assert generator_model() == "nvidia/nemotron-3-super-120b-a12b"


def test_judge_model_raises_by_name_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="JUDGE_MODEL"):
        judge_model()


def test_generator_model_raises_by_name_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GENERATOR_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="GENERATOR_MODEL"):
        generator_model()

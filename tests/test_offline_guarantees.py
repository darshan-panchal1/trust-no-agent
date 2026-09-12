"""T4.6: the offline guarantees, verified as mechanisms rather than intentions — an opt-out
that looks set and does nothing is worse than none (Article III.a)."""

from __future__ import annotations

import os
import tomllib
from typing import cast

import pytest

import conftest
from tests.repo_files import REPO_ROOT


class _LiveItem:
    """The two attributes `pytest_collection_modifyitems` actually touches."""

    def __init__(self) -> None:
        self.keywords = {"live": True}
        self.own_markers: list[pytest.MarkDecorator] = []

    def add_marker(self, marker: pytest.MarkDecorator) -> None:
        self.own_markers.append(marker)


def test_env_block_opt_outs_took_effect_before_import(pytestconfig: pytest.Config) -> None:
    """FR-036 + Trap 28: set in pyproject's `env` block, which needs pytest-env to work.
    `DEEPEVAL_DISABLE_DOTENV` alone can't beat deepeval's plugin-import-time
    `autoload_dotenv()` (conftest.py cleans up instead) — this proves the declaration is real."""
    assert os.environ.get("DEEPEVAL_TELEMETRY_OPT_OUT") == "YES"
    assert os.environ.get("RAGAS_DO_NOT_TRACK") == "true"
    assert os.environ.get("DEEPEVAL_DISABLE_DOTENV") == "1"
    # `env` is not a pytest core ini key: reading it back proves pytest-env is loaded and
    # the block is not being silently ignored, which is the failure III.a warns about.
    assert pytestconfig.pluginmanager.hasplugin("env")
    assert "DEEPEVAL_TELEMETRY_OPT_OUT=YES" in pytestconfig.getini("env")
    assert "DEEPEVAL_DISABLE_DOTENV=1" in pytestconfig.getini("env")


def test_default_configuration_excludes_live_tests() -> None:
    """FR-049: exclusion is a property of the default config, not something to ask for."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    assert "not live" in config["tool"]["pytest"]["ini_options"]["addopts"]


def test_the_live_marker_alone_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """FR-047: one switch is never enough — a marker copied from docs must not spend."""
    monkeypatch.delenv("EVAL_LIVE", raising=False)
    item = _LiveItem()
    conftest.pytest_collection_modifyitems([cast(pytest.Item, item)])
    assert [marker.name for marker in item.own_markers] == ["skip"]


def test_both_switches_together_let_a_live_test_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_LIVE", "1")
    item = _LiveItem()
    conftest.pytest_collection_modifyitems([cast(pytest.Item, item)])
    assert item.own_markers == []

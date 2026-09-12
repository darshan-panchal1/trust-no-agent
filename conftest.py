"""Article XI: forces `run_async=False` for every real `assert_test` call, in exactly one
place. Defends against `copy_metrics()` (`deepeval/metrics/utils.py`), which rebuilds each
metric via `type(metric)(**valid_args)` — silently dropping any ctor arg not stored under a
matching attribute (Trap 1). `test_harness_integrity.py` is exempt: reproducing that is its
whole purpose.
"""

from __future__ import annotations

import os

import pytest
from _pytest.config import Config
from _pytest.terminal import TerminalReporter
from deepeval.dataset import Golden
from deepeval.evaluate import assert_test as _real_assert_test
from deepeval.metrics import BaseConversationalMetric, BaseMetric
from deepeval.test_case import ConversationalTestCase, LLMTestCase

from evals import cost
from evals.cost_table import format_cost_table

# Above: `deepeval.evaluate`, not `deepeval` — the top-level name is dynamic, mypy-invisible
# (Trap 21). Same object.

# Trap 28: deepeval's pytest11 plugin imports `deepeval`, which autoloads `.env` before any
# hook (including pytest-env's) can run. Nothing at pytest-config level beats that; cleaning
# up here, before collection, is the earliest point this repo's own code controls.
for _leaked_credential in ("NVIDIA_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
    os.environ.pop(_leaked_credential, None)


def assert_test(
    test_case: LLMTestCase | ConversationalTestCase | None = None,
    metrics: list[BaseMetric] | list[BaseConversationalMetric] | None = None,
    golden: Golden | None = None,
) -> None:
    """The one sanctioned call into deepeval's `assert_test` outside the harness-integrity
    test — every real behavior test imports this, never the library function directly."""
    _real_assert_test(test_case=test_case, metrics=metrics, golden=golden, run_async=False)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """FR-047's second switch — the marker alone never spends money. `-m live` collects live
    tests; they're skipped here unless `EVAL_LIVE=1` too, reported skipped, never silent."""
    if os.environ.get("EVAL_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="live scoring needs -m live AND EVAL_LIVE=1 (FR-047)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.hookimpl(trylast=True)
def pytest_terminal_summary(terminalreporter: TerminalReporter, config: Config) -> None:
    """Article VIII: the cost table prints after every run, with no flag to ask for it.
    `trylast=True` because deepeval's plugin writes a summary too — without it the table
    is printed but buried, and Article VIII asks for it *at the end*."""
    terminalreporter.write_line("")
    terminalreporter.write_line(format_cost_table(cost.rows()))

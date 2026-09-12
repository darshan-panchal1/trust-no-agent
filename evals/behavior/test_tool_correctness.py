"""T3.5 / Article II.a: all three ToolCorrectness configurations scored on the same
trajectory, side by side — the lesson is that a green tool-correctness number is a
statement about configuration, not about the agent (docs/api-notes.md Verification 2).
Fully offline and deterministic: `available_tools` stays unset, so the metric never
reaches for a model, and this suite is green with `OPENAI_API_KEY` absent (Trap 16).
"""

from __future__ import annotations

import pytest
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase, ToolCall

from conftest import assert_test
from evals.judge import build_tool_correctness_metric

pytestmark = pytest.mark.deepeval

EXTRA_CALL_CASE = LLMTestCase(
    input="q",
    actual_output="a",
    tools_called=[
        ToolCall(name="lookup_policy", input_parameters=None),
        ToolCall(name="cross_reference", input_parameters=None),
        ToolCall(name="lookup_glossary", input_parameters=None),
    ],
    expected_tools=[
        ToolCall(name="lookup_policy", input_parameters=None),
        ToolCall(name="cross_reference", input_parameters=None),
    ],
)


def test_default_ignores_extra_calls() -> None:
    metrics: list[BaseMetric] = [build_tool_correctness_metric()]
    assert_test(EXTRA_CALL_CASE, metrics)


def test_ordering_aware_still_ignores_extra_calls() -> None:
    metrics: list[BaseMetric] = [build_tool_correctness_metric(should_consider_ordering=True)]
    assert_test(EXTRA_CALL_CASE, metrics)


def test_exact_match_penalises_extra_calls() -> None:
    metrics: list[BaseMetric] = [build_tool_correctness_metric(should_exact_match=True)]
    with pytest.raises(AssertionError):
        assert_test(EXTRA_CALL_CASE, metrics)

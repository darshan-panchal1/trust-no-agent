"""Article II.b: deepeval + `evals.golden` (plus the framework-free `app.models` output
type) only — never `ragas`. `GoldenCase` + `AgentResult` -> `LLMTestCase`.
"""

from __future__ import annotations

from deepeval.test_case import LLMTestCase, ToolCall

from app.models import AgentResult
from evals.golden.schema import GoldenCase


def to_llm_test_case(case: GoldenCase, result: AgentResult) -> LLMTestCase:
    """One DeepEval test case per (golden case, agent output) pair."""
    expected_tools = (
        [ToolCall(name=name, input_parameters=None) for name in case.expected_tools]
        if case.expected_tools
        else None
    )
    return LLMTestCase(
        input=case.question,
        actual_output=result.answer,
        expected_output=case.ground_truth,
        retrieval_context=[chunk.text for chunk in result.retrieved_contexts],
        tools_called=[
            ToolCall(name=call.name, input_parameters=dict(call.arguments))
            for call in result.tool_calls
        ],
        expected_tools=expected_tools,
    )

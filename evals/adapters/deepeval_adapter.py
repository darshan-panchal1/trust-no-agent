"""Article II.b: deepeval + framework-free inputs (`evals.golden`, `app.models`,
`evals.contract`) only — never `ragas`. `GoldenCase` + `AgentResult`, or a caller's
`EvalRecord`, -> `LLMTestCase`.
"""

from __future__ import annotations

from deepeval.test_case import LLMTestCase, ToolCall

from app.models import AgentResult
from evals.contract import EvalRecord
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


def record_to_test_case(record: EvalRecord) -> LLMTestCase:
    """The per-record path's test case. RefusalCorrectness renders only input, actual and
    expected output, so the GEval prompt — and its evidence key — matches the v1 path's."""
    if record.input is None or record.output is None:
        raise ValueError("an LLMTestCase needs both input and output")
    return LLMTestCase(
        input=record.input,
        actual_output=record.output,
        expected_output=record.expected,
        retrieval_context=None if record.contexts is None else list(record.contexts),
    )

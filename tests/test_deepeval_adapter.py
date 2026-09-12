"""T3.3 acceptance: no ragas import; `tools_called` is a list of `ToolCall` with correct
fields (Article II.b)."""

from __future__ import annotations

import inspect

from app.models import AgentResult, RetrievedChunk, ToolCallRecord
from evals.adapters import deepeval_adapter
from evals.adapters.deepeval_adapter import to_llm_test_case
from evals.golden.schema import GoldenCase


def test_no_ragas_import() -> None:
    source = inspect.getsource(deepeval_adapter)
    assert "import ragas" not in source
    assert "from ragas" not in source


def test_tools_called_has_correct_fields() -> None:
    case = GoldenCase(
        question="q",
        ground_truth="gt",
        reference_contexts=[],
        category="multi-hop",
        expected_tools=["lookup_policy"],
    )
    result = AgentResult(
        answer="a",
        retrieved_contexts=[RetrievedChunk(text="t", source_document="doc.md", score=1.0)],
        tool_calls=[ToolCallRecord(name="lookup_policy", arguments={"document": "doc.md"})],
        latency_ms=1.0,
    )
    test_case = to_llm_test_case(case, result)
    tools_called = test_case.tools_called
    expected_tools = test_case.expected_tools
    assert tools_called is not None
    assert expected_tools is not None
    assert len(tools_called) == 1
    assert tools_called[0].name == "lookup_policy"
    assert tools_called[0].input_parameters == {"document": "doc.md"}
    assert expected_tools[0].name == "lookup_policy"

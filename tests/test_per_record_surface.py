"""T021 (US1, FR-001/005, SC-005): one synchronous call, no framework import on the caller's
side, a cached re-run identical to the first, and a programming error that still raises."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from evals import cost
from tests.per_record_support import golden_record
from tests.source_ast import imports_any
from trustnoagent import EvalRecord, EvalResult, evaluate

ID = "tna.ragas.faithfulness"


def test_evaluate_is_a_plain_synchronous_call() -> None:
    assert not inspect.iscoroutinefunction(evaluate)


def test_a_caller_needs_no_framework_import() -> None:
    assert not imports_any(Path(__file__), ("ragas", "deepeval", "openai", "instructor"))


@pytest.mark.usefixtures("socket_disabled")
def test_a_second_identical_call_is_the_same_result_served_from_evidence() -> None:
    _, record = golden_record("v2_fixed", 0)
    first = evaluate(ID, record)
    before = {row.call_kind: (row.calls, row.cached) for row in cost.rows()}
    second = evaluate(ID, record)
    after = {row.call_kind: (row.calls, row.cached) for row in cost.rows()}
    assert isinstance(second, EvalResult) and second == first and first.status == "ok"
    for kind, (calls, cached) in after.items():
        prior_calls, prior_cached = before.get(kind, (0, 0))
        assert calls - prior_calls == cached - prior_cached, kind


def test_a_non_record_is_a_programming_error() -> None:
    not_a_record: Any = {"input": "q", "output": "a"}
    with pytest.raises(TypeError, match="EvalRecord"):
        evaluate(ID, not_a_record)
    assert EvalRecord(input="q").present("input")

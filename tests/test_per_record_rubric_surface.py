"""T045 (US4): `evaluate()` widens to `str | RubricJudge` without disturbing the five built-in
string ids, and `list_evaluators(*rubrics)` appends each rubric after the built-ins. mypy checks
both call shapes below — this file is the static half of the widening."""

from __future__ import annotations

import inspect

import pytest

import trustnoagent
from evals.rubric import RubricJudge
from tests.per_record_support import golden_record
from trustnoagent import evaluate, list_evaluators

POLITE = RubricJudge(
    "polite", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)


def test_the_signature_names_both_accepted_types() -> None:
    annotation = str(inspect.signature(evaluate).parameters["evaluator"].annotation)
    assert "str" in annotation and "RubricJudge" in annotation
    assert trustnoagent.RubricJudge is RubricJudge


@pytest.mark.usefixtures("socket_disabled")
@pytest.mark.parametrize("ident", [info.id for info in list_evaluators()])
def test_every_built_in_string_id_still_scores_a_committed_record(ident: str) -> None:
    result = evaluate(ident, golden_record("v2_fixed", 1)[1])
    assert result.status == "ok", (ident, result.error)
    assert result.evaluator_id == ident


def test_rubrics_are_listed_after_the_built_ins_with_the_deepeval_version() -> None:
    listed = list_evaluators(POLITE)
    assert [i.id for i in listed[:-1]] == [i.id for i in list_evaluators()]
    rubric = listed[-1]
    assert (rubric.id, rubric.output_type) == ("tna.judge.polite", "label")
    assert rubric.requires == POLITE.requires
    assert rubric.version == f"{trustnoagent.__version__}+deepeval@4.2.0"


def test_a_rubric_is_still_never_found_by_its_id_string() -> None:
    """No process-wide rubric registry (research R15): the string tells the caller what to do."""
    result = evaluate(POLITE.id, golden_record("v2_fixed", 1)[1])
    assert result.status == "error" and "RubricJudge definition" in (result.error or "")

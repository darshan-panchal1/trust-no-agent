"""Layer-free answers the facade gives before any scorer runs: a programming error raises, and
an id nothing answers to is a result naming it (spec FR-004). Imports neither eval layer."""

from __future__ import annotations

from collections.abc import Iterable

from evals import outcomes
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo
from evals.rubric import RubricJudge


def require_types(evaluator: object, record: object) -> None:
    """Programming errors raise (spec FR-004); everything at evaluation time is a status."""
    if not isinstance(evaluator, (str, RubricJudge)):
        kind = type(evaluator).__name__
        raise TypeError(f"evaluator must be an id string or a RubricJudge, not {kind}")
    if not isinstance(record, EvalRecord):
        raise TypeError(f"record must be an EvalRecord, not {type(record).__name__}")


def unknown_evaluator(evaluator: str, known: Iterable[str]) -> EvalResult:
    """No version, and answered before any judge configuration is read."""
    info = EvaluatorInfo(evaluator, "", frozenset(), "score")
    if evaluator.startswith("tna.judge."):
        message = f"{evaluator!r} is a rubric judge: pass its RubricJudge definition, not its id"
    else:
        message = f"unknown evaluator {evaluator!r}; known ids: {', '.join(known)}"
    return outcomes.error(info, message)

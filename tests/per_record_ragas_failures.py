"""What ragas really raises for an unusable judge reply — not collected. Probed on instructor
1.16.0 with a mocked NIM: a bad reply is `InstructorRetryException` with `last_completion` set,
an HTTP failure the same class with it unset, truncation `IncompleteOutputException`."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import pytest
from instructor.exceptions import IncompleteOutputException, InstructorRetryException
from pydantic import BaseModel, ValidationError
from ragas.exceptions import RagasOutputParserException

from evals.component import record_eval

JUDGE_TEXT = '{"nonsense": 1}'


def completion(text: str) -> SimpleNamespace:
    call = SimpleNamespace(function=SimpleNamespace(arguments=text))
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])


def retry(last_completion: object) -> InstructorRetryException:
    return InstructorRetryException(
        "x", last_completion=last_completion, n_attempts=4, total_usage=None
    )


def _validation_error() -> ValidationError:
    class Shape(BaseModel):
        verdict: int

    try:
        Shape.model_validate({"verdict": "x"})
    except ValidationError as exc:
        return exc
    raise AssertionError("unreachable")


BAD_REPLIES: dict[str, Callable[[], object]] = {
    "nan": lambda: float("nan"),
    "parser": RagasOutputParserException,
    "validation": _validation_error,
    "bad_reply": lambda: retry(completion(JUDGE_TEXT)),
    "truncated": lambda: IncompleteOutputException(last_completion=completion(JUDGE_TEXT)),
}


def score_with(monkeypatch: pytest.MonkeyPatch, produce: Callable[[], object]) -> None:
    """Replace the layer's scoring call with one that returns or raises what `produce` makes."""

    def score(_metric: object, _record: object) -> float:
        outcome = produce()
        if isinstance(outcome, BaseException):
            raise outcome
        return float(outcome)  # type: ignore[arg-type]

    monkeypatch.setattr(record_eval, "_score", score)

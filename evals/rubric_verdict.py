"""What a rubric judge is asked, and what it may answer (spec 001, US4). Framework-free
(Article II.c). The prompt names the reply format exactly, and the verdict model enforces it —
strictly, so `"3"` is not a score and `"Pass"` is not `"pass"`."""

from __future__ import annotations

from functools import cache
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, create_model

from evals.contract import EvalRecord, RecordField
from evals.rubric import RubricJudge

_ORDER: tuple[RecordField, ...] = ("input", "output", "expected", "contexts")


def _field(record: EvalRecord, name: RecordField) -> str:
    if name == "contexts":
        return "\n".join(f"[{i}] {text}" for i, text in enumerate(record.contexts or (), 1))
    return str(getattr(record, name))


def _reply_format(rubric: RubricJudge) -> str:
    if rubric.labels is not None:
        answer = f'"label": one of {", ".join(repr(label) for label in rubric.labels)}'
    else:
        low, high = rubric.score_range or (0, 0)
        answer = f'"score": a number from {low:g} to {high:g}'
    return f'Reply with one JSON object and nothing else: {{{answer}, "reason": one sentence}}'


def render_prompt(rubric: RubricJudge, record: EvalRecord) -> str:
    """Instructions, then only the fields the rubric requires, then the exact reply format."""
    shown = [f"{name}:\n{_field(record, name)}" for name in _ORDER if name in rubric.requires]
    return "\n\n".join([rubric.instructions.strip(), *shown, _reply_format(rubric)])


@cache
def verdict_model(rubric: RubricJudge) -> type[BaseModel]:
    verdict: Any
    if rubric.labels is not None:
        verdict = ("label", Literal[rubric.labels])  # exact match already: "Pass" is not "pass"
    else:
        low, high = rubric.score_range or (0, 0)
        verdict = ("score", Annotated[float, Field(ge=low, le=high, strict=True)])
    name, annotation = verdict
    fields: dict[str, Any] = {name: (annotation, ...), "reason": (str, ...)}
    model: type[BaseModel] = create_model("RubricVerdict", **fields)
    return model


def verdict_schema(rubric: RubricJudge) -> dict[str, Any]:
    """The fingerprint's output-schema component: exactly what the judge is held to."""
    return verdict_model(rubric).model_json_schema()

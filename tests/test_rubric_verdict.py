"""T040, second half (US4): a rubric's prompt shows only the fields it requires plus the exact
reply format, and its verdict schema accepts only what the rubric allows — strictly."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evals.contract import EvalRecord
from evals.rubric import RubricJudge
from evals.rubric_verdict import render_prompt, verdict_model

PASS_FAIL = RubricJudge(
    "tone", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)
SCALE = RubricJudge("depth", "Rate the depth.", frozenset({"input", "output"}), score_range=(1, 5))
RECORD = EvalRecord(input="the question", output="the answer", expected="the reference")


def test_the_prompt_renders_only_the_required_fields_and_the_reply_format() -> None:
    prompt = render_prompt(PASS_FAIL, RECORD)
    assert "Is the answer polite?" in prompt and "the answer" in prompt
    assert "the question" not in prompt and "the reference" not in prompt
    assert '"label"' in prompt and "pass" in prompt and "fail" in prompt


def test_the_verdict_schema_accepts_only_what_the_rubric_allows() -> None:
    assert verdict_model(PASS_FAIL).model_validate_json('{"label": "pass", "reason": "x"}')
    assert verdict_model(SCALE).model_validate_json('{"score": 3, "reason": "x"}')
    rejected = [
        (PASS_FAIL, '{"label": "maybe", "reason": "x"}'), (PASS_FAIL, "{}"),
        (SCALE, '{"score": 7, "reason": "x"}'), (SCALE, '{"score": "3", "reason": "x"}'),
    ]
    for model, text in rejected:
        with pytest.raises(ValidationError):
            verdict_model(model).model_validate_json(text)

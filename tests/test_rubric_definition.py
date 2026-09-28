"""T040 (US4, FR-020/022): a rubric definition is validated when it is made, its identity moves
with every piece of content, and its prompt and verdict schema say exactly what it asks for."""

from __future__ import annotations

import pytest

from evals.rubric import RubricJudge

PASS_FAIL = RubricJudge(
    "tone", "Is the answer polite?", frozenset({"output"}), labels=("pass", "fail")
)
SCALE = RubricJudge("depth", "Rate the depth.", frozenset({"input", "output"}), score_range=(1, 5))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "Tone"}, {"name": "tone-x"}, {"name": ""},  # name outside ^[a-z0-9_]+$
        {"labels": None},  # neither labels nor range
        {"score_range": (1.0, 5.0)},  # both
        {"labels": ("pass", "pass")}, {"labels": ()},  # duplicate / empty label set
        {"instructions": " "}, {"requires": frozenset()}, {"requires": frozenset({"trace"})},
    ],
)
def test_an_invalid_definition_is_refused_when_made(kwargs: dict[str, object]) -> None:
    fields: dict[str, object] = {"name": "tone", "instructions": "Is it polite?",
                                 "requires": frozenset({"output"}), "labels": ("pass", "fail")}
    with pytest.raises(ValueError):
        RubricJudge(**{**fields, **kwargs})  # type: ignore[arg-type]


@pytest.mark.parametrize("bounds", [(5, 5), (5, 1)])
def test_a_score_range_must_run_low_to_high(bounds: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        RubricJudge("depth", "Rate it.", frozenset({"output"}), score_range=bounds)


def test_identity_and_output_type() -> None:
    assert (PASS_FAIL.id, PASS_FAIL.output_type) == ("tna.judge.tone", "label")
    assert (SCALE.id, SCALE.output_type) == ("tna.judge.depth", "score")


@pytest.mark.parametrize(
    "changed",
    [{"instructions": "Is it rude?"}, {"requires": frozenset({"input", "output"})},
     {"labels": ("pass", "fail", "unsure")}],
)
def test_every_piece_of_content_moves_the_template_version(changed: dict[str, object]) -> None:
    fields: dict[str, object] = {"name": "tone", "instructions": "Is the answer polite?",
                                 "requires": frozenset({"output"}), "labels": ("pass", "fail")}
    moved = RubricJudge(**{**fields, **changed})  # type: ignore[arg-type]
    assert moved.template_version != PASS_FAIL.template_version
    rescaled = RubricJudge("depth", "Rate the depth.", SCALE.requires, score_range=(1, 10))
    assert rescaled.template_version != SCALE.template_version

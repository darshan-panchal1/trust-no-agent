"""US3's structural guarantee: an `EvalResult` cannot be built carrying a verdict it has no right
to (spec FR-014). Beyond the builders' discipline, so a future one that forgets fails at
construction, loudly, in the code that made the mistake — never as a silent 0 downstream."""

from __future__ import annotations

import pytest

from evals.contract import EvalResult


@pytest.mark.parametrize("status", ["error", "skipped", "invalid_output"])
@pytest.mark.parametrize("verdict", [{"score": 0.0}, {"score": 1.0}, {"label": "pass"}])
def test_a_failed_result_cannot_carry_a_score_or_label(
    status: str, verdict: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="verdict"):
        EvalResult("tna.x", "v", status, **verdict)  # type: ignore[arg-type]


def test_nan_is_never_a_score_even_on_an_ok_result() -> None:
    with pytest.raises(ValueError, match="NaN"):
        EvalResult("tna.x", "v", "ok", score=float("nan"))


def test_the_legitimate_shapes_still_construct() -> None:
    assert EvalResult("tna.x", "v", "ok", score=0.0).score == 0.0  # zero is a real score
    assert EvalResult("tna.x", "v", "ok", label="pass").label == "pass"
    assert EvalResult("tna.x", "v", "error", error="boom").score is None

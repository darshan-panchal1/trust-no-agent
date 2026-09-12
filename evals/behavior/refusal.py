"""RefusalCorrectness (FR-022/023): judges whether an out-of-scope question was correctly
refused, and whether an answerable one was wrongly refused. Built through the T3.1 factory
only (Article VI.a) — no bare `GEval(` call in this module.
"""

from __future__ import annotations

from typing import Literal

from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from evals.judge import build_geval_metric

_STEPS = [
    (
        "Check 'expected_output' to determine whether the question should have been "
        "refused (out-of-scope) or answered (answerable)."
    ),
    (
        "If refusal was expected, 'actual_output' must decline to answer and must not "
        "fabricate a policy-sounding response."
    ),
    (
        "If an answer was expected, 'actual_output' must not refuse or deflect — a "
        "wrongful refusal is as much a failure here as a wrongful answer."
    ),
    (
        "Score high only when the refuse/answer decision made in 'actual_output' matches "
        "what 'expected_output' called for; score low otherwise, regardless of writing "
        "quality."
    ),
]


def build_refusal_correctness_metric(mode: Literal["offline", "live"] = "offline") -> GEval:
    return build_geval_metric(
        name="RefusalCorrectness",
        evaluation_steps=_STEPS,
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        mode=mode,
    )

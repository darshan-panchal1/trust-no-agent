"""The GEval factory (FR-023/024): evaluation steps only — `criteria` is not an accepted
parameter at all, so forwarding it is a `TypeError`, not a runtime choice. Supplying
`criteria` instead would trigger a second judge call to auto-generate steps, doubling cost
and stored evidence per case for no benefit once the steps are already known
(docs/api-notes.md V3.5).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from evals.judge.cached import CachedJudge

_DEFAULT_PARAMS: tuple[SingleTurnParams, ...] = (
    SingleTurnParams.INPUT,
    SingleTurnParams.ACTUAL_OUTPUT,
)


def build_geval_metric(
    name: str,
    evaluation_steps: list[str],
    evaluation_params: Sequence[SingleTurnParams] = _DEFAULT_PARAMS,
    threshold: float = 0.5,
    mode: Literal["offline", "live"] = "offline",
) -> GEval:
    if not evaluation_steps:
        raise ValueError("build_geval_metric requires non-empty evaluation_steps")
    return GEval(
        name=name,
        evaluation_params=list(evaluation_params),
        evaluation_steps=evaluation_steps,
        threshold=threshold,
        model=CachedJudge(f"deepeval:{name.lower()}", mode=mode),
    )

"""Article II.b's shape, ops-side: deepeval only, never ragas. `RefusalCorrectness` scored
for one variant under a caller-supplied cache namespace.

The namespaced metric is rebuilt from the real one's own `evaluation_steps` and
`evaluation_params`, so the rendered judge prompt is byte-identical: GEval's
`generate_evaluation_results.txt` interpolates the steps, the test case and the parameters,
and never the metric `name` (checked against the installed template, not assumed). Same
instrument, different cache label — so the comparison against `thresholds.yaml`'s bar is
measuring what set that bar.
"""

from __future__ import annotations

from typing import Literal

from deepeval.metrics import GEval

from app.models import AgentResult
from evals.adapters.deepeval_adapter import to_llm_test_case
from evals.behavior.live_pass import RELEVANT_CATEGORIES
from evals.behavior.refusal import build_refusal_correctness_metric
from evals.golden.schema import GoldenCase
from evals.judge import build_geval_metric

Mode = Literal["offline", "live"]
METRIC_NAME = "RefusalCorrectness"


def _metric(namespace: str, mode: Mode) -> GEval:
    base = build_refusal_correctness_metric(mode=mode)
    if not namespace:
        return base
    steps, params = base.evaluation_steps, base.evaluation_params
    assert steps is not None and params is not None  # the factory always sets both
    return build_geval_metric(
        name=f"{namespace}{METRIC_NAME}", evaluation_steps=steps, evaluation_params=params,
        mode=mode,
    )


def refusal_gate_mean(
    cases: list[GoldenCase], answers: list[AgentResult], namespace: str, mode: Mode
) -> float:
    """Mean over the refuse/answer-relevant cases only — the same subset that set the bar."""
    metric = _metric(namespace, mode)
    scores: list[float] = []
    for case, result in zip(cases, answers):
        if case.category not in RELEVANT_CATEGORIES:
            continue
        metric.measure(to_llm_test_case(case, result))
        assert metric.score is not None  # set by measure(); None only before first use
        scores.append(metric.score)
    return sum(scores) / len(scores)

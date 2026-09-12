"""The threshold-free half of the ragas re-scoring pass — shared by `calibrate` (which
will *produce* thresholds from these) and `evals/ops/summary_ragas.py` (which *consumes*
one via `threshold_for`), so there is one offline re-scoring implementation, not two.
"""

from __future__ import annotations

from ragas import EvaluationDataset, MultiTurnSample, SingleTurnSample, evaluate
from ragas.dataset_schema import EvaluationResult

from app.models import AgentResult
from evals.adapters.ragas_adapter import to_single_turn_sample
from evals.component.matrix import METRIC_NAMES, build_metrics, mean_score
from evals.golden.schema import GoldenCase


def _evaluate(cases: list[GoldenCase], variant_answers: list[AgentResult]) -> EvaluationResult:
    samples: list[SingleTurnSample | MultiTurnSample] = [
        to_single_turn_sample(c, a) for c, a in zip(cases, variant_answers)
    ]
    result = evaluate(
        EvaluationDataset(samples=samples),
        metrics=build_metrics(mode="offline"),
        raise_exceptions=True,
        show_progress=False,
    )
    assert isinstance(result, EvaluationResult)  # `return_executor` unset, so never Executor
    return result


def ragas_results(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> dict[str, EvaluationResult]:
    return {
        variant: _evaluate(cases, variant_answers) for variant, variant_answers in answers.items()
    }


def mean_pair(results: dict[str, EvaluationResult], name: str) -> tuple[float, float]:
    return mean_score(results["v1_naive"], name), mean_score(results["v2_fixed"], name)


def ragas_means(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> dict[str, tuple[float, float]]:
    """`{metric_name: (v1_mean, v2_mean)}` — no threshold read, none needed."""
    results = ragas_results(cases, answers)
    return {name: mean_pair(results, name) for name in METRIC_NAMES}

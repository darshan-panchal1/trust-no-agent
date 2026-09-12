"""FR-042/048: the ragas half of `build_summary` — one `MetricRow` and its worst
regressions per metric. Mean computation lives in `evals/ops/ragas_means.py`, shared with
`calibrate`; this module only attaches the threshold (where Article IV names one) and
builds regressions. Two of the four ragas metrics — `context_precision`/`response_relevancy`
— are diagnostic only (not in Article IV's gate table) and get `threshold=None`.
"""

from __future__ import annotations

from app.models import AgentResult
from evals.component.matrix import METRIC_NAMES
from evals.gate_policy import GATED_METRICS
from evals.golden.schema import GoldenCase
from evals.ops.ragas_means import mean_pair, ragas_results
from evals.ops.run_summary import MetricRow, Regression
from evals.thresholds import threshold_for


def ragas_rows(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> tuple[list[MetricRow], list[Regression]]:
    results = ragas_results(cases, answers)
    rows: list[MetricRow] = []
    regressions: list[Regression] = []
    for name in METRIC_NAMES:
        v1, v2 = mean_pair(results, name)
        threshold = threshold_for(name) if name in GATED_METRICS else None
        rows.append(MetricRow(metric=name, v1_mean=v1, v2_mean=v2, threshold=threshold))
        for variant, result in results.items():
            for case, answer, score in zip(cases, answers[variant], result[name]):
                regressions.append(
                    Regression(
                        metric=name,
                        question=case.question,
                        variant=variant,
                        score=float(score),
                        answer=answer.answer,
                    )
                )
    return rows, regressions

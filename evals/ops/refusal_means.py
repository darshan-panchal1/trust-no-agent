"""The threshold-free half of the `RefusalCorrectness` re-scoring pass — shared by
`calibrate` (which will *produce* a threshold from these) and
`evals/ops/summary_behavior.py` (which *consumes* one via `threshold_for`).
"""

from __future__ import annotations

from app.models import AgentResult
from evals.adapters.deepeval_adapter import to_llm_test_case
from evals.behavior.live_pass import RELEVANT_CATEGORIES
from evals.behavior.refusal import build_refusal_correctness_metric
from evals.golden.schema import GoldenCase

METRIC_NAME = "RefusalCorrectness"

Triple = tuple[GoldenCase, AgentResult, float]


def measured(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> dict[str, list[Triple]]:
    """One `(case, answer, score)` triple per relevant case per variant — the single place
    `RefusalCorrectness.measure()` is ever called, offline, from cache."""
    relevant = [(i, c) for i, c in enumerate(cases) if c.category in RELEVANT_CATEGORIES]
    metric = build_refusal_correctness_metric(mode="offline")
    out: dict[str, list[Triple]] = {}
    for variant, variant_answers in answers.items():
        triples: list[Triple] = []
        for i, case in relevant:
            answer = variant_answers[i]
            metric.measure(to_llm_test_case(case, answer))
            assert metric.score is not None  # set by measure(); None only before first use
            triples.append((case, answer, metric.score))
        out[variant] = triples
    return out


def mean(triples: list[Triple]) -> float:
    return sum(score for _, _, score in triples) / len(triples)


def refusal_means(
    cases: list[GoldenCase], answers: dict[str, list[AgentResult]]
) -> tuple[float, float]:
    """`(v1_mean, v2_mean)` — no threshold read, none needed."""
    triples = measured(cases, answers)
    return mean(triples["v1_naive"]), mean(triples["v2_fixed"])

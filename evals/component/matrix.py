"""The four Ragas metrics (diagnostic layer, Article II) and per-metric mean scores.

Names are pinned explicitly (`name=`) rather than trusting each class's library default —
`LLMContextPrecisionWithReference` defaults to `llm_context_precision_with_reference` and
`ResponseRelevancy` to `answer_relevancy`, neither matching this repo's file/task naming.
"""

from __future__ import annotations

from typing import Literal

from ragas.dataset_schema import EvaluationResult
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)
from ragas.metrics.base import Metric, SingleTurnMetric

from evals.embeddings import build_judge_embeddings
from evals.ragas_llm import build_judge_llm

METRIC_NAMES = ("faithfulness", "context_recall", "context_precision", "response_relevancy")


def build_metric(name: str, mode: Literal["offline", "live"] = "offline") -> SingleTurnMetric:
    """One metric with its own cached judge (Trap 19 fix). Only `response_relevancy` builds
    embeddings — so scoring one other metric live never imports the calibration group."""
    llm = build_judge_llm(name, mode)
    metric: SingleTurnMetric
    if name == "faithfulness":
        metric = Faithfulness(name=name, llm=llm)
    elif name == "context_recall":
        metric = LLMContextRecall(name=name, llm=llm)
    elif name == "context_precision":
        metric = LLMContextPrecisionWithReference(name=name, llm=llm)
    elif name == "response_relevancy":
        metric = ResponseRelevancy(name=name, llm=llm, embeddings=build_judge_embeddings(mode))
    else:
        raise KeyError(f"no ragas metric named {name!r}; expected one of {METRIC_NAMES}")
    return metric


def build_metrics(mode: Literal["offline", "live"] = "offline") -> list[Metric]:
    """Every metric, in `METRIC_NAMES` order — the v1 path's exact set."""
    return [build_metric(name, mode) for name in METRIC_NAMES]


def mean_score(result: EvaluationResult, metric_name: str) -> float:
    """Mean of one metric's column across every golden case (diagnostic only, T2.6)."""
    return float(result.to_pandas()[metric_name].mean())

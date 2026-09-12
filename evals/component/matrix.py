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
from ragas.metrics.base import Metric

from evals.embeddings import build_judge_embeddings
from evals.ragas_llm import build_judge_llm

METRIC_NAMES = ("faithfulness", "context_recall", "context_precision", "response_relevancy")


def build_metrics(mode: Literal["offline", "live"] = "offline") -> list[Metric]:
    """One metric instance per name, each with its own cached judge (Trap 19 fix)."""
    return [
        Faithfulness(name="faithfulness", llm=build_judge_llm("faithfulness", mode)),
        LLMContextRecall(name="context_recall", llm=build_judge_llm("context_recall", mode)),
        LLMContextPrecisionWithReference(
            name="context_precision", llm=build_judge_llm("context_precision", mode)
        ),
        ResponseRelevancy(
            name="response_relevancy",
            llm=build_judge_llm("response_relevancy", mode),
            embeddings=build_judge_embeddings(mode),
        ),
    ]


def mean_score(result: EvaluationResult, metric_name: str) -> float:
    """Mean of one metric's column across every golden case (diagnostic only, T2.6)."""
    return float(result.to_pandas()[metric_name].mean())

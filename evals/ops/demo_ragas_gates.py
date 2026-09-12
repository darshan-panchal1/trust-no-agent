"""Article II.b's shape, ops-side: ragas only, never deepeval. The two *gated* ragas metrics,
scored for one variant under a caller-supplied cache namespace.

Two of ragas' four metrics, not all four: `context_precision` and `response_relevancy` gate
nothing (Article IV's table), and dropping `response_relevancy` drops the embeddings
dependency with it — so the demo runs on a plain `uv sync`, no calibration group.
"""

from __future__ import annotations

from typing import Literal

from ragas import EvaluationDataset, MultiTurnSample, SingleTurnSample, evaluate
from ragas.dataset_schema import EvaluationResult
from ragas.metrics import Faithfulness, LLMContextRecall
from ragas.metrics.base import Metric

from app.models import AgentResult
from evals.adapters.ragas_adapter import to_single_turn_sample
from evals.component.matrix import mean_score
from evals.golden.schema import GoldenCase
from evals.ragas_llm import build_judge_llm

Mode = Literal["offline", "live"]
RAGAS_GATES = ("faithfulness", "context_recall")


def _metrics(namespace: str, mode: Mode) -> list[Metric]:
    """`namespace=""` reads v2's committed `ragas:*` evidence; a non-empty one keys into
    `ragas:<namespace><metric>`, which no calibration entry can occupy."""
    return [
        Faithfulness(name="faithfulness", llm=build_judge_llm(f"{namespace}faithfulness", mode)),
        LLMContextRecall(
            name="context_recall", llm=build_judge_llm(f"{namespace}context_recall", mode)
        ),
    ]


def ragas_gate_means(
    cases: list[GoldenCase], answers: list[AgentResult], namespace: str, mode: Mode
) -> dict[str, float]:
    samples: list[SingleTurnSample | MultiTurnSample] = [
        to_single_turn_sample(c, a) for c, a in zip(cases, answers)
    ]
    result = evaluate(
        EvaluationDataset(samples=samples),
        metrics=_metrics(namespace, mode),
        raise_exceptions=True,
        show_progress=False,
    )
    assert isinstance(result, EvaluationResult)  # `return_executor` unset, so never Executor
    return {name: mean_score(result, name) for name in RAGAS_GATES}

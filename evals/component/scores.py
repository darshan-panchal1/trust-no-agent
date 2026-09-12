"""T2.5a — the session-scoped, offline-only score matrix.

No `mode` parameter on this fixture's surface: Article III's determinism budget means every
default test run reads exclusively from committed cache. A miss anywhere in the pipeline
(generation or judging) skips the whole matrix with the missing-key diagnosis intact.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest
from ragas import EvaluationDataset, MultiTurnSample, SingleTurnSample, evaluate
from ragas.dataset_schema import EvaluationResult

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.adapters.ragas_adapter import to_single_turn_sample
from evals.cache.store import CacheMiss
from evals.component.matrix import build_metrics
from evals.golden.load import load_golden

VariantAnswer = Callable[[str], AgentResult]


def _evaluate_variant(answer_fn: VariantAnswer) -> EvaluationResult:
    samples: list[SingleTurnSample | MultiTurnSample] = [
        to_single_turn_sample(case, answer_fn(case.question)) for case in load_golden()
    ]
    dataset = EvaluationDataset(samples=samples)
    result = evaluate(dataset, metrics=build_metrics(), raise_exceptions=True, show_progress=False)
    # evaluate() only returns an Executor when return_executor=True, which we never pass.
    return cast(EvaluationResult, result)


@pytest.fixture(scope="session")
def score_matrix() -> dict[str, EvaluationResult]:
    """`{"v1_naive": ..., "v2_fixed": ...}`, each a full Ragas `EvaluationResult`."""
    try:
        return {"v1_naive": _evaluate_variant(v1_answer), "v2_fixed": _evaluate_variant(v2_answer)}
    except CacheMiss as exc:
        pytest.skip(f"cache not yet populated — {exc}")

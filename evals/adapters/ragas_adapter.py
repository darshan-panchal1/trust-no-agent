"""Article II.b: ragas + `evals.golden` (plus the framework-free `app.models` output type)
only — never `deepeval`. `GoldenCase` + `AgentResult` -> `SingleTurnSample`.
"""

from __future__ import annotations

from ragas import SingleTurnSample

from app.models import AgentResult
from evals.golden.schema import GoldenCase


def to_single_turn_sample(case: GoldenCase, result: AgentResult) -> SingleTurnSample:
    """One ragas sample per (golden case, agent output) pair — no raw filenames in content."""
    return SingleTurnSample(
        user_input=case.question,
        retrieved_contexts=[chunk.text for chunk in result.retrieved_contexts],
        reference=case.ground_truth,
        response=result.answer,
    )

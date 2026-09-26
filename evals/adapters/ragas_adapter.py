"""Article II.b: ragas + framework-free inputs (`evals.golden`, `app.models`,
`evals.contract`) only — never `deepeval`. `GoldenCase` + `AgentResult`, or a caller's
`EvalRecord`, -> `SingleTurnSample`.
"""

from __future__ import annotations

from ragas import SingleTurnSample

from app.models import AgentResult
from evals.contract import EvalRecord
from evals.golden.schema import GoldenCase


def to_single_turn_sample(case: GoldenCase, result: AgentResult) -> SingleTurnSample:
    """One ragas sample per (golden case, agent output) pair — no raw filenames in content."""
    return SingleTurnSample(
        user_input=case.question,
        retrieved_contexts=[chunk.text for chunk in result.retrieved_contexts],
        reference=case.ground_truth,
        response=result.answer,
    )


def record_to_sample(record: EvalRecord) -> SingleTurnSample:
    """The per-record path's sample. For a golden-derived record it equals
    `to_single_turn_sample`'s field for field, so the rendered prompts — and therefore the
    committed evidence keys — are the same."""
    return SingleTurnSample(
        user_input=record.input,
        retrieved_contexts=None if record.contexts is None else list(record.contexts),
        reference=record.expected,
        response=record.output,
    )

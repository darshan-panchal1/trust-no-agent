"""Shared helpers for the per-record tests — not collected (no `test_` prefix). Imports
neither eval layer (Article II.c): records come from the app, judging from the facade."""

from __future__ import annotations

from collections.abc import Callable

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.contract import EvalRecord
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase

_VARIANTS: dict[str, Callable[..., AgentResult]] = {"v1_naive": v1_answer, "v2_fixed": v2_answer}


def golden_record(variant: str, index: int) -> tuple[GoldenCase, EvalRecord]:
    """One committed golden case and its offline answer, as a caller would supply them."""
    case = load_golden()[index]
    result = _VARIANTS[variant](case.question, mode="offline")
    record = EvalRecord(
        input=case.question,
        output=result.answer,
        expected=case.ground_truth,
        contexts=tuple(chunk.text for chunk in result.retrieved_contexts),
    )
    return case, record

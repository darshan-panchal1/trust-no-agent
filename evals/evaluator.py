"""The `Evaluator` protocol and its listing entry (Article II.c). Structural: nothing
inherits it on either side of the facade, so it spans no framework — each per-layer module
satisfies it by shape alone. Framework-free, like `evals/contract.py`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from evals.contract import EvalRecord, EvalResult, OutputType, RecordField

if TYPE_CHECKING:
    from evals.judge_config import JudgeConfig


@dataclass(frozen=True)
class EvaluatorInfo:
    id: str
    version: str
    requires: frozenset[RecordField]
    output_type: OutputType


class Evaluator(Protocol):
    id: str
    version: str
    requires: frozenset[RecordField]
    output_type: OutputType

    def evaluate(self, record: EvalRecord, judge: JudgeConfig) -> EvalResult: ...

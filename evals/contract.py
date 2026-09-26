"""The per-record evaluator contract's values (spec 001, data-model.md). Framework-free by
Article II.c: plain literals and frozen dataclasses, no ragas or deepeval type anywhere, so a
value crossing the routing facade carries nothing from either layer. The structural
`Evaluator` protocol lives beside it in `evals/evaluator.py`."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["offline", "live"]  # the one definition; `trustnoagent.Mode` re-exports it
Status = Literal["ok", "error", "skipped", "invalid_output"]
OutputType = Literal["score", "label", "bool"]
Provenance = Literal["recorded", "not_recorded"]
RecordField = Literal["input", "output", "expected", "contexts"]


@dataclass(frozen=True)
class EvalRecord:
    input: str | None = None
    output: str | None = None
    expected: str | None = None
    contexts: tuple[str, ...] | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)  # never sent to a judge

    def present(self, name: RecordField) -> bool:
        """Absent means None. An empty string or tuple is present, and is scored."""
        return getattr(self, name) is not None


@dataclass(frozen=True)
class EvalResult:
    """`score`/`label` are set only when `status == "ok"` — never 0 or NaN for a failure."""

    evaluator_id: str
    evaluator_version: str
    status: Status
    score: float | None = None
    label: str | None = None
    explanation: str | None = None
    judge_model: str | None = None
    judge_fingerprint: str | None = None
    fingerprint_provenance: Provenance | None = None
    latency_ms: int = field(default=0, compare=False)  # measured, so never part of equality
    tokens_in: int | None = None
    tokens_out: int | None = None
    error: str | None = None
    raw: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Structural, so a builder that forgets fails where it is written (spec FR-014)."""
        if self.status != "ok" and (self.score is not None or self.label is not None):
            raise ValueError(f"a {self.status!r} result cannot carry a verdict (score or label)")
        if self.score is not None and math.isnan(self.score):
            raise ValueError("a score cannot be NaN: it is invalid_output, never a number")


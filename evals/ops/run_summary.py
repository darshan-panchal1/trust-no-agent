"""FR-042's one shared data structure — both renderings read it, so they cannot disagree.
Every derived figure is computed here, never in a template."""

from __future__ import annotations

import datetime
from pathlib import Path

from pydantic import BaseModel

from evals.cost import CostRow


class MetricRow(BaseModel):
    """`threshold=None` marks a diagnostic-only metric — Article IV names three gates;
    the rest are scored but never gate anything."""

    metric: str
    v1_mean: float
    v2_mean: float
    threshold: float | None = None

    @property
    def delta(self) -> float:
        return self.v2_mean - self.v1_mean

    @property
    def margin(self) -> float | None:
        return None if self.threshold is None else self.v2_mean - self.threshold

    @property
    def separates(self) -> bool | None:
        """v1 below the gate, v2 at or above it (Article IV). `None` if there is no gate."""
        return None if self.threshold is None else self.v1_mean < self.threshold <= self.v2_mean


class Regression(BaseModel):
    """One bad case with the text that produced it. FR-042: the answer is the load-bearing
    field — a confident, fluent, wrong answer sitting next to the score that caught it."""

    metric: str
    question: str
    variant: str
    score: float
    answer: str


class RunSummary(BaseModel):
    generated_at: datetime.datetime
    metrics: list[MetricRow]
    worst_regressions: list[Regression]  # the five worst, chosen when the summary is built
    costs: list[CostRow]

    def save(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> RunSummary:
        return cls.model_validate_json(path.read_text())

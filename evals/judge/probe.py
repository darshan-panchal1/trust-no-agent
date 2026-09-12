"""Article XI / T3.6: the score-laundering reproduction metric, routed through this
package's one door like every other DeepEval metric. Mirrors docs/api-notes.md's `M`
exactly — `score` is stored under a mismatched attribute name (`self.injected`), which is
precisely what makes `copy_metrics()`'s vars()-intersected-with-ctor-params rebuild drop it
and substitute the class default instead.
"""

from __future__ import annotations

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class _ScoreLaunderingProbe(BaseMetric):  # type: ignore[no-untyped-call]
    # BaseMetric.__init_subclass__ calls deepeval's own untyped observe_methods(cls).
    def __init__(self, threshold: float = 0.5, score: float = 0.9) -> None:
        self.threshold = threshold
        self.injected = score  # ctor arg `score` stored under a DIFFERENT name — the bug

    def measure(self, test_case: LLMTestCase, *args: object, **kwargs: object) -> float:
        assert self.threshold is not None  # narrows BaseMetric's Optional[float] for mypy
        self.score = self.injected
        self.success = self.score >= self.threshold
        self.reason = "score-laundering probe"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args: object, **kwargs: object) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return bool(self.success)

    @property
    def __name__(self) -> str:
        return "ScoreLaunderingProbe"


def build_score_laundering_probe(score: float, threshold: float = 0.5) -> BaseMetric:
    """Deliberately fails when `score < threshold`, e.g. `score=0.1, threshold=0.5`."""
    return _ScoreLaunderingProbe(threshold=threshold, score=score)

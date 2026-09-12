"""Article II.a: all three ToolCorrectness configurations, built the same way, so a
viewer can see the same trajectory score differently under each. Fully deterministic when
`available_tools=None` — `StubJudge` proves it, by raising if the metric ever reaches for a
model (docs/api-notes.md Verification 2).
"""

from __future__ import annotations

from deepeval.metrics import ToolCorrectnessMetric

from evals.judge.stub import StubJudge


def build_tool_correctness_metric(
    *, should_exact_match: bool = False, should_consider_ordering: bool = False
) -> ToolCorrectnessMetric:
    return ToolCorrectnessMetric(
        model=StubJudge(),
        should_exact_match=should_exact_match,
        should_consider_ordering=should_consider_ordering,
    )

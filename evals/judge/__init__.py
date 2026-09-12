"""evals.judge — the one door (Article VI.a): every DeepEval metric or judge model in this
repo is constructed here, never by a bare constructor call anywhere else, including tests.
Split into small modules to hold Article VII's 60-line cap; the import surface stays this
package, so `evals.judge.*` is what VI.a's enforcement checks against.
"""

from __future__ import annotations

from evals.judge.cached import CachedJudge
from evals.judge.geval import build_geval_metric
from evals.judge.probe import build_score_laundering_probe
from evals.judge.tool_correctness import build_tool_correctness_metric

__all__ = [
    "CachedJudge",
    "build_geval_metric",
    "build_score_laundering_probe",
    "build_tool_correctness_metric",
]

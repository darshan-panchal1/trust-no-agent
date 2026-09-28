"""Public API — the smallest surface that runs, gates, and reports one evaluation. See
CONSTITUTION.md Article X: no provider registry, no plugin system. `evals`/`app` remain the
real internal layout (facade, not a rename) — see the packaging plan for why.
"""

from __future__ import annotations

from evals.contract import EvalRecord, EvalResult, Mode
from evals.evaluator import EvaluatorInfo
from evals.judge_config import JudgeConfig
from evals.ops.run_summary import RunSummary
from evals.rubric import RubricJudge
from trustnoagent.evaluators import evaluate, list_evaluators
from trustnoagent.suite import EvalSuite, run_gate
from trustnoagent.version import __version__

# v1.0.0's five names are unchanged; v1.1.0 adds the per-record contract (additive only).
__all__ = [
    "EvalRecord",
    "EvalResult",
    "EvalSuite",
    "EvaluatorInfo",
    "JudgeConfig",
    "Mode",
    "RubricJudge",
    "RunSummary",
    "__version__",
    "evaluate",
    "list_evaluators",
    "run_gate",
]

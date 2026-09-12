"""Public API — the smallest surface that runs, gates, and reports one evaluation. See
CONSTITUTION.md Article X: no provider registry, no plugin system. `evals`/`app` remain the
real internal layout (facade, not a rename) — see the packaging plan for why.
"""

from __future__ import annotations

from evals.ops.run_summary import RunSummary
from trustnoagent.suite import EvalSuite, Mode, run_gate

__version__ = "1.0.0"

__all__ = ["EvalSuite", "Mode", "RunSummary", "__version__", "run_gate"]

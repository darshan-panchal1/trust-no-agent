"""Which metrics gate a pass, and how tight `compare` may run — both derived from
measurement, not authored. `evals/thresholds.py` reads/validates the versioned data file
these produce; this module is the policy that decides what goes into it.
"""

from __future__ import annotations

# Article IV's separating-gate table, verbatim: exactly these three metrics gate a pass.
# `context_precision`/`response_relevancy` (the other two of ragas' four) and
# `ToolCorrectness` (II.a) are scored but never appear here — diagnostic only, no threshold.
# This is "the code" Article V's schema test checks `thresholds.yaml` against.
GATED_METRICS = ("faithfulness", "context_recall", "RefusalCorrectness")

# FR-043's noise band, sized to measured judge non-determinism, not guessed — full
# re-scoring data (4 live runs/metric) in docs/api-notes.md, "judge noise floor".
COMPARISON_TOLERANCE = 0.15
COMPARISON_TOLERANCE_JUSTIFICATION = (
    "1.5x the largest same-run noise spread measured (faithfulness, n=4, spread=0.0947, "
    "min=0.8040/max=0.8987/stdev=0.0434), rounded to 0.05 — see docs/api-notes.md"
)

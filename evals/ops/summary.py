"""FR-042/048: builds the `RunSummary` `record` was always supposed to produce, entirely
from what's already cached — no live call, no new spend. `record()` calls this only after
a real (non-dry-run) run, once every entry it needs is guaranteed present.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals import cost
from evals.golden.load import load_golden
from evals.ops.run_summary import RunSummary
from evals.ops.summary_behavior import refusal_row
from evals.ops.summary_ragas import ragas_rows

_WORST_REGRESSIONS = 5
VARIANTS = (("v1_naive", v1_answer), ("v2_fixed", v2_answer))


def build_summary() -> RunSummary:
    cases = load_golden()
    answers: dict[str, list[AgentResult]] = {
        variant: [answer_fn(c.question, mode="offline") for c in cases]
        for variant, answer_fn in VARIANTS
    }
    metrics, regressions = ragas_rows(cases, answers)
    behavior_row, behavior_regressions = refusal_row(cases, answers)
    metrics.append(behavior_row)
    regressions.extend(behavior_regressions)
    regressions.sort(key=lambda r: r.score)
    return RunSummary(
        generated_at=datetime.datetime.now(datetime.UTC),
        metrics=metrics,
        worst_regressions=regressions[:_WORST_REGRESSIONS],
        costs=cost.rows(),
    )


def write_summary(path: Path) -> None:
    """`record()`'s save step, factored out so the CLI command stays a thin caller."""
    path.parent.mkdir(parents=True, exist_ok=True)
    build_summary().save(path)

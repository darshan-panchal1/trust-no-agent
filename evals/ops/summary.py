"""FR-042/048: builds the `RunSummary` `record` was always supposed to produce, entirely
from what's already cached — no live call, no new spend. `record()` calls this only after
a real (non-dry-run) run, once every entry it needs is guaranteed present.

`mode` reaches generation only (`app.v1_naive`/`app.v2_fixed`, hence `generate:*` cache
keys). `ragas_rows`/`refusal_row` score through `ragas_means.py`/`refusal_means.py`, which
hardcode `mode="offline"` for the judge — a live-generated answer with no pre-populated
judge cache entry raises `CacheMiss` at scoring. Loud, not a silent partial live-mode.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Literal

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals import cost
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase
from evals.ops.run_summary import RunSummary
from evals.ops.summary_behavior import refusal_row
from evals.ops.summary_ragas import ragas_rows

_WORST_REGRESSIONS = 5
VARIANTS = (("v1_naive", v1_answer), ("v2_fixed", v2_answer))


def build_summary(
    cases: list[GoldenCase] | None = None,
    mode: Literal["offline", "live"] = "offline",
) -> RunSummary:
    resolved_cases = load_golden() if cases is None else cases
    answers: dict[str, list[AgentResult]] = {
        variant: [answer_fn(c.question, mode=mode) for c in resolved_cases]
        for variant, answer_fn in VARIANTS
    }
    metrics, regressions = ragas_rows(resolved_cases, answers)
    behavior_row, behavior_regressions = refusal_row(resolved_cases, answers)
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

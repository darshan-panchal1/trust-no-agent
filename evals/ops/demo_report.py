"""The demo's on-screen output, including Article VIII's cost table (printed unconditionally,
tokens exact, an unpriced call reading UNVERIFIED rather than a fabricated figure). Score
rendering lives in `evals/ops/demo_scores.py`.

The vibes gate is imported from `tests/` on purpose: Article IV defines "looks fine" as
whatever that gate accepts, so the demo asserts against the same mechanism the suite uses
rather than a second opinion written here.
"""

from __future__ import annotations

from app.models import AgentResult
from evals import cost
from evals.cost_table import format_cost_table
from evals.golden.schema import GoldenCase
from evals.ops.demo_scores import Means, print_scores
from tests.vibes_checks import assert_deterministic_vibes


def _vibes(text: str) -> str:
    try:
        assert_deterministic_vibes(text)
        return "vibes gate: PASS"
    except AssertionError as exc:
        return f"vibes gate: FAIL ({exc})"


def _side_by_side(case: GoldenCase, real: AgentResult, regressed: AgentResult) -> None:
    print(f"\n{'=' * 96}\nQUESTION  [{case.category}]  {case.question}\n{'=' * 96}")
    print(f"\n--- real v2_fixed  ({_vibes(real.answer)})\n\n{real.answer}\n")
    print(f"--- regressed v2   ({_vibes(regressed.answer)})\n\n{regressed.answer}\n")


def print_report(
    cases: list[GoldenCase], real: list[AgentResult], regressed: list[AgentResult],
    real_means: Means, regressed_means: Means, shown: int,
) -> None:
    _side_by_side(cases[shown], real[shown], regressed[shown])
    print_scores(real_means, regressed_means)
    print(f"\n{format_cost_table(cost.rows())}")

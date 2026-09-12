"""The demo: a two-line prompt edit to v2 that reads as tidying up, leaves retrieval byte-
identical, keeps every answer fluent — and breaks both gates capable of catching it.

This regression only touches answer generation. `context_recall`'s ragas implementation
reads only `user_input`/`retrieved_contexts`/`reference` (verified from source, never
`response`), so it structurally cannot detect a generation-only regression — not a noise
question, an applicability one. `evals/ops/demo_report.py` reports it as such: 2 of 2
*applicable* gates broken (faithfulness, RefusalCorrectness), not "2 of 3".

Real v2 is scored strictly `mode="offline"` (`read_or_raise`, structurally unable to write),
so its numbers are the committed calibration evidence itself. Only the regressed variant
calls live, and every entry it writes carries a `regression_demo:` call_kind. Nothing here
can reach a v1/v2 calibration key.

Run: `uv run python -c "from evals.ops.regression_demo import main; main()"` (needs
NVIDIA_API_KEY) — or `main(mode="offline")` to replay entirely from the committed
`regression_demo:*` evidence: no key, no network, same numbers.
"""

from __future__ import annotations

from typing import Literal

from app.models import AgentResult
from app.v2_fixed import answer as real_v2_answer
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase
from evals.ops.demo_ragas_gates import ragas_gate_means
from evals.ops.demo_refusal_gate import refusal_gate_mean
from evals.ops.demo_report import print_report
from evals.ops.demo_variant import answer as regressed_answer

NAMESPACE = "regression_demo:"
# Confirmed fabrication ("Meridian observes 10 paid holidays each year.") against real v2's
# correct refusal — a sharper, more legible side-by-side than a generic out-of-scope case.
SHOWCASE_QUESTION = "How many paid holidays does Meridian observe each year?"


def gate_means(
    cases: list[GoldenCase],
    answers: list[AgentResult],
    namespace: str,
    mode: Literal["offline", "live"],
) -> dict[str, float]:
    means = ragas_gate_means(cases, answers, namespace, mode)
    means["RefusalCorrectness"] = refusal_gate_mean(cases, answers, namespace, mode)
    return means


def main(mode: Literal["offline", "live"] = "live") -> None:
    """`mode="offline"` replays the regressed variant from its own committed
    `regression_demo:*` evidence — no key, no network, matching `build_summary`'s pattern.
    Real v2 stays offline unconditionally either way; see the module docstring."""
    cases = load_golden()
    real = [real_v2_answer(c.question) for c in cases]  # offline: cannot write, cannot spend
    regressed = [regressed_answer(c.question, mode=mode) for c in cases]
    real_means = gate_means(cases, real, "", "offline")
    regressed_means = gate_means(cases, regressed, NAMESPACE, mode)
    shown = next(i for i, c in enumerate(cases) if c.question == SHOWCASE_QUESTION)
    print_report(cases, real, regressed, real_means, regressed_means, shown)

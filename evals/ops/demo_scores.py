"""The demo's score table against `evals/thresholds.yaml`'s real bars.

This demo regresses only the answer-generation prompt. `context_recall`'s ragas
implementation reads exclusively `user_input`/`retrieved_contexts`/`reference` (confirmed
against the installed `LLMContextRecall._ascore`, never `response`) — so no prompt-only
regression can move it, by construction, independent of the judge noise floor documented
in docs/api-notes.md. It stays in the table for transparency; it is not one of the gates
this regression is scored against.
"""

from __future__ import annotations

from evals.gate_policy import GATED_METRICS
from evals.thresholds import load_thresholds

Means = dict[str, float]

NOT_APPLICABLE = {
    "context_recall": (
        "n/a — reads only retrieval/reference, never the answer; structurally cannot "
        "detect a generation-only regression like this one"
    ),
}


def print_scores(real: Means, regressed: Means) -> None:
    thresholds = load_thresholds()
    header = f"{'metric':<22}{'bar':>9}{'real v2':>10}{'regressed':>11}{'delta':>9}   verdict"
    print(f"{'=' * 96}\n{header}")
    broken = 0
    applicable = [m for m in GATED_METRICS if m not in NOT_APPLICABLE]
    for name in GATED_METRICS:
        bar = thresholds.metrics[name].value
        before, after = real[name], regressed[name]
        if name in NOT_APPLICABLE:
            verdict = NOT_APPLICABLE[name]
        elif after >= bar:
            verdict = "pass"
        else:
            verdict = "FAIL — broke the gate"
            broken += 1
        print(
            f"{name:<22}{bar:>9.4f}{before:>10.4f}{after:>11.4f}{after - before:>+9.4f}   {verdict}"
        )
    print(f"\n{broken} of {len(applicable)} applicable gates broken ({', '.join(applicable)})")

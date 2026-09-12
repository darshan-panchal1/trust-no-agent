"""The observed v1/v2 means for exactly `GATED_METRICS`, offline, from committed evidence.

Its own module so the two consumers stay separated: `calibrate` *writes* thresholds from
these, `tests/test_separation_contract.py` *checks* the committed thresholds against them.
Article I.a means pytest must never import the module that rewrites `thresholds.yaml`, so
the shared half lives here rather than in `calibrate.py`.
"""

from __future__ import annotations

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals import gate_policy
from evals.golden.load import load_golden
from evals.ops.ragas_means import ragas_means
from evals.ops.refusal_means import refusal_means

VARIANTS = (("v1_naive", v1_answer), ("v2_fixed", v2_answer))


def observed_means() -> dict[str, tuple[float, float]]:
    """`{metric: (v1_mean, v2_mean)}` for exactly `GATED_METRICS`, offline, from cache."""
    cases = load_golden()
    answers: dict[str, list[AgentResult]] = {
        variant: [answer_fn(c.question, mode="offline") for c in cases]
        for variant, answer_fn in VARIANTS
    }
    means = ragas_means(cases, answers)
    means["RefusalCorrectness"] = refusal_means(cases, answers)
    return {name: means[name] for name in gate_policy.GATED_METRICS}

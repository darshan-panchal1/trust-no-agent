"""T3.8a — Slice 3's live pass, the only place in this slice that ever passes `mode="live"`.
Populates `deepeval:refusalcorrectness` cache entries by scoring `RefusalCorrectness`
against both variants' live-mode answers, for the golden cases where refuse/answer is the
question. Run by hand, once, with a real `NVIDIA_API_KEY`. Never part of `pytest`; never
CI.

Run: `uv run python -c "from evals.behavior.live_pass import main; main()"`
"""

from __future__ import annotations

from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.adapters.deepeval_adapter import to_llm_test_case
from evals.behavior.refusal import build_refusal_correctness_metric
from evals.golden.load import load_golden

VARIANTS = (("v1_naive", v1_answer), ("v2_fixed", v2_answer))
RELEVANT_CATEGORIES = ("out-of-scope", "answerable")


def main() -> None:
    cases = [c for c in load_golden() if c.category in RELEVANT_CATEGORIES]
    metric = build_refusal_correctness_metric(mode="live")
    for variant_name, answer_fn in VARIANTS:
        for case in cases:
            result = answer_fn(case.question, mode="live")
            metric.measure(to_llm_test_case(case, result))
        print(f"{variant_name}: {len(cases)} refusal-correctness cases scored and cached")

"""T2.5b — Slice 2's live pass, the only place in Slice 2 that ever passes `mode="live"`.

Run by hand, once, with a real `NVIDIA_API_KEY`, to populate the `ragas:*` cache entries
(and any not-yet-cached `generate:*` entries from T1.9) this slice's component tests read
from. Never part of `pytest`; never CI. Embeddings need no credential (Ninth amendment) —
just `uv sync --group calibration` first, for the local model this pulls in on first use.

Run: `uv run python -c "from evals.component.live_pass import main; main()"`
"""

from __future__ import annotations

from ragas import EvaluationDataset, MultiTurnSample, SingleTurnSample, evaluate

from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.adapters.ragas_adapter import to_single_turn_sample
from evals.component.matrix import build_metrics
from evals.golden.load import load_golden

VARIANTS = (("v1_naive", v1_answer), ("v2_fixed", v2_answer))


def main() -> None:
    cases = load_golden()
    for variant_name, answer_fn in VARIANTS:
        samples: list[SingleTurnSample | MultiTurnSample] = [
            to_single_turn_sample(case, answer_fn(case.question, mode="live")) for case in cases
        ]
        dataset = EvaluationDataset(samples=samples)
        evaluate(
            dataset, metrics=build_metrics(mode="live"), raise_exceptions=True, show_progress=False
        )
        print(f"{variant_name}: {len(samples)} samples scored and cached")

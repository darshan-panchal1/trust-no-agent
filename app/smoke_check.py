"""Manual smoke test — the only place in Slice 1 that ever passes `mode="live"`.

Run by hand, once, with a real `NVIDIA_API_KEY`, to populate the `generate:*` cache
entries this slice's other tests read from. Never part of `pytest`; never CI.
"""

from __future__ import annotations

from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer

QUESTIONS = [
    "What is the current per diem rate for business travel meals?",
    "Can a Senior Manager approve their own $2,500 international trip?",
    "What is Meridian Logistics' policy on cryptocurrency compensation?",
]


def main() -> None:
    for question in QUESTIONS:
        v1_result = v1_answer(question, mode="live")
        v2_result = v2_answer(question, mode="live")
        print(f"\n=== {question} ===")
        print(f"[v1_naive] {v1_result.answer}")
        print(f"[v2_fixed] {v2_result.answer}")


if __name__ == "__main__":
    main()

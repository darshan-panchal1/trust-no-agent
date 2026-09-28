"""The per-record contract's hand-run live pass (spec 001, T057). Never run by pytest or CI: it
makes real NIM calls, which Article VIII reports UNVERIFIED (no dated NIM price exists). Needs
NVIDIA_API_KEY, JUDGE_MODEL and GENERATOR_MODEL exported, and `uv sync --group calibration` for
live `tna.ragas.response_relevancy`. Writes only to a fresh temp cache_dir, never the committed
store. Run: `uv run python -c "from trustnoagent.live_check import main; main()"`"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from evals import cost
from evals.contract import EvalRecord, EvalResult
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from trustnoagent import evaluate, list_evaluators

_Q = "How many unused PTO days can I carry into next year?"
_CONTEXTS = (
    ("Full-time employees accrue 15 PTO days per year during their first two years, "
     "increasing to 20 days from year three onward."),
    ("Up to 5 unused PTO days may be carried into the following calendar year. Days beyond "
     "that cap are forfeited unless local law requires otherwise."),
)
_EXPECTED = "Up to 5 unused PTO days carry over; days beyond the cap are forfeited."
_GOOD = "You can carry over up to 5 unused PTO days; the rest are forfeited."
_BAD = "All of them. Meridian has unlimited PTO, so nothing is forfeited. Look it up yourself."
RECORDS = {  # one faithful answer, one known-bad: wrong, ungrounded and rude
    "good": EvalRecord(_Q, _GOOD, _EXPECTED, _CONTEXTS),
    "bad": EvalRecord(_Q, _BAD, _EXPECTED, _CONTEXTS),
}
RUBRIC = RubricJudge("polite_and_grounded", "Answer 'pass' only if the answer is polite AND "
                     "consistent with the contexts; otherwise 'fail'.",
                     frozenset({"output", "contexts"}), labels=("pass", "fail"))


def _pass(config: JudgeConfig, cache_dir: Path, show: bool) -> list[EvalResult]:
    evaluators: list[str | RubricJudge] = [*(info.id for info in list_evaluators()), RUBRIC]
    results = [evaluate(e, r, config, cache_dir) for r in RECORDS.values() for e in evaluators]
    for name, r in zip([n for n in RECORDS for _ in evaluators], results, strict=True):
        verdict = r.label if r.label is not None else r.score
        detail = (r.explanation or r.error or "")[:110]
        if show:
            print(f"{name:4} {r.evaluator_id:34} {r.status:7} {verdict!s:7} tokens="
                  f"{r.tokens_in}/{r.tokens_out} fp={(r.judge_fingerprint or '-')[:12]}  {detail}")
    return results


def main() -> None:
    if not os.environ.get("NVIDIA_API_KEY"):
        raise SystemExit("NVIDIA_API_KEY is not set: this pass makes real NIM calls")
    config, cache_dir = JudgeConfig.from_env(mode="live"), Path(tempfile.mkdtemp(prefix="tna-"))
    print(f"judge={config.judge_model} cache_dir={cache_dir}")
    first = _pass(config, cache_dir, show=True)
    uncached = sum(row.calls - row.cached for row in cost.rows())
    second = _pass(config, cache_dir, show=False)
    rerun = sum(row.calls - row.cached for row in cost.rows()) - uncached
    print(f"first pass uncached calls={uncached}; re-run uncached calls={rerun}; "
          f"identical results={first == second}")

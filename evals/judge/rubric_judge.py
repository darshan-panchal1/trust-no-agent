"""The rubric judge (spec 001, US4), built here because Article VI.a's one door is this package:
every judge model in this repo is constructed in `evals/judge/`. It is the same `CachedJudge`
GEval uses — one NIM client, one evidence store, one `json_completion` — under its own
`call_kind`, `deepeval:judge.<name>`, which is Article III's existing `deepeval:<metric>` form."""

from __future__ import annotations

from typing import Literal

from evals.judge.cached import CachedJudge


def build_rubric_judge(name: str, mode: Literal["offline", "live"] = "offline") -> CachedJudge:
    return CachedJudge(f"deepeval:judge.{name}", mode=mode)

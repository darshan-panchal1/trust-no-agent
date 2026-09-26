"""Layer-free result helpers for the routing facade, kept apart so `evaluators.py` — the one
module Article II.c lets import both eval layers — stays small. Imports neither layer."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import replace

from evals import outcomes
from evals.cache.store import CacheMiss
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo

_MAX_MESSAGE = 500  # a provider's error body can be huge; a result should stay readable


def require_types(evaluator: object, record: object) -> None:
    """Programming errors raise (spec FR-004); everything at evaluation time is a status."""
    if not isinstance(evaluator, str):
        raise TypeError(f"evaluator must be an id string, not {type(evaluator).__name__}")
    if not isinstance(record, EvalRecord):
        raise TypeError(f"record must be an EvalRecord, not {type(record).__name__}")


def unknown_evaluator(evaluator: str, known: Iterable[str]) -> EvalResult:
    """An id nothing answers to is a result naming it, not a `KeyError` (spec FR-004). It has
    no version, and it is answered before any judge configuration is read."""
    info = EvaluatorInfo(evaluator, "", frozenset(), "score")
    if evaluator.startswith("tna.judge."):
        message = f"{evaluator!r} is a rubric judge: pass its RubricJudge definition, not its id"
    else:
        message = f"unknown evaluator {evaluator!r}; known ids: {', '.join(known)}"
    return outcomes.error(info, message)


def failure(info: EvaluatorInfo, exc: Exception) -> EvalResult:
    """The FR-004 safety net: whatever an evaluator raised, the caller gets a status. A cache
    miss says what to do for a caller's own record — `record` only refreshes the built-in set."""
    if isinstance(exc, CacheMiss):
        key = str(exc).split(" — ")[0]
        message = f"{key}: no committed evidence covers this record; score it in live mode"
    else:
        message = f"{type(exc).__name__}: {exc}"
    return outcomes.error(info, message[:_MAX_MESSAGE])


def no_directory(info: EvaluatorInfo) -> EvalResult:
    """Outside a repo checkout the committed store is off limits (spec FR-032): say so."""
    message = "no cache_dir given and this is not a repo checkout: pass cache_dir="
    return outcomes.error(info, message)


def finish(result: EvalResult, record: EvalRecord, started: float) -> EvalResult:
    """Stamp measured latency, and carry a caller's record metadata through to `raw`."""
    raw = {**result.raw, "metadata": dict(record.metadata)} if record.metadata else result.raw
    return replace(result, raw=raw, latency_ms=round((time.monotonic() - started) * 1000))

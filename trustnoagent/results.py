"""Layer-free result helpers for the routing facade, kept apart so `evaluators.py` — the one
module Article II.c lets import both eval layers — stays small. Imports neither layer."""

from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import replace

from evals import outcomes
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo


def unknown_evaluator(evaluator: str, known: Iterable[str]) -> EvalResult:
    """An id nothing answers to is a result naming it, not a `KeyError` (spec FR-004). It has
    no version, and it is answered before any judge configuration is read."""
    info = EvaluatorInfo(evaluator, "", frozenset(), "score")
    return outcomes.error(info, f"unknown evaluator {evaluator!r}; known ids: {', '.join(known)}")


def no_directory(info: EvaluatorInfo) -> EvalResult:
    """Outside a repo checkout the committed store is off limits (spec FR-032): say so."""
    message = "no cache_dir given and this is not a repo checkout: pass cache_dir="
    return outcomes.error(info, message)


def finish(result: EvalResult, record: EvalRecord, started: float) -> EvalResult:
    """Stamp measured latency, and carry a caller's record metadata through to `raw`."""
    raw = {**result.raw, "metadata": dict(record.metadata)} if record.metadata else result.raw
    return replace(result, raw=raw, latency_ms=round((time.monotonic() - started) * 1000))

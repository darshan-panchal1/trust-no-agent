"""The routing facade — Article II.c's single named exception. It routes one caller record to
one evaluator by id and returns that evaluator's own result; it never combines, averages or
compares results, and imports no framework itself. Built-ins are registered by direct import
(Article X: no plugins, no discovery). Synchronous throughout (Article X: no async)."""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

from evals.behavior import record_eval as refusal
from evals.cache import location, store
from evals.component import record_eval as component
from evals.contract import EvalRecord, EvalResult, RecordField
from evals.evaluator import EvaluatorInfo
from evals.judge_config import JudgeConfig
from trustnoagent.results import failure, finish, no_directory, require_types, unknown_evaluator
from trustnoagent.version import __version__

Scorer = Callable[[EvaluatorInfo, EvalRecord, JudgeConfig], EvalResult]
_BUILT_INS: dict[str, tuple[Scorer, frozenset[RecordField], str]] = {
    **{
        f"tna.ragas.{name}": (partial(component.evaluate_ragas, name), needs, component.LIB)
        for name, needs in component.REQUIRES.items()
    },
    "tna.deepeval.refusal_correctness": (refusal.evaluate_refusal, refusal.REQUIRES, refusal.LIB),
}
REGISTRY: dict[str, Scorer] = {key: scorer for key, (scorer, _, _) in _BUILT_INS.items()}
INFOS: dict[str, EvaluatorInfo] = {
    key: EvaluatorInfo(key, f"{__version__}+{lib}", needs, "score")
    for key, (_, needs, lib) in _BUILT_INS.items()
}


def evaluate(
    evaluator: str, record: EvalRecord, judge: JudgeConfig | None = None,
    cache_dir: Path | None = None,
) -> EvalResult:
    require_types(evaluator, record)
    if (info := INFOS.get(evaluator)) is None:
        return unknown_evaluator(evaluator, sorted(INFOS))
    started = time.monotonic()
    try:  # nothing an evaluator raises escapes: it becomes a status (spec FR-004)
        config = judge or JudgeConfig.from_env()
        directory = cache_dir or location.default_cache_dir(store.CACHE_DIR)
        if directory is None:
            result = no_directory(info)
        else:
            with location.override(directory):
                result = REGISTRY[evaluator](info, record, config)
    except Exception as exc:  # noqa: BLE001 — the point: any failure becomes a result
        result = failure(info, exc)
    return finish(result, record, started)


def list_evaluators() -> list[EvaluatorInfo]:
    """Every built-in, sorted by id. Needs no credentials, env vars or network (FR-012)."""
    return [INFOS[key] for key in sorted(INFOS)]

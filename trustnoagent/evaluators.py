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
from trustnoagent.results import finish, no_directory, unknown_evaluator
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
    if not isinstance(evaluator, str):
        raise TypeError(f"evaluator must be an id string, not {type(evaluator).__name__}")
    if not isinstance(record, EvalRecord):
        raise TypeError(f"record must be an EvalRecord, not {type(record).__name__}")
    if (info := INFOS.get(evaluator)) is None:
        return unknown_evaluator(evaluator, sorted(INFOS))
    config = judge or JudgeConfig.from_env()
    directory = cache_dir or location.default_cache_dir(store.CACHE_DIR)
    if directory is None:
        return no_directory(info)
    started = time.monotonic()
    with location.override(directory):
        result = REGISTRY[evaluator](info, record, config)
    return finish(result, record, started)


def list_evaluators() -> list[EvaluatorInfo]:
    """Every built-in, sorted by id. Needs no credentials, env vars or network (FR-012)."""
    return [INFOS[key] for key in sorted(INFOS)]

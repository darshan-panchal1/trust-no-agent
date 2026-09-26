"""The routing facade — Article II.c's single named exception. It resolves an id, or a caller's
rubric, to exactly one evaluator and returns that evaluator's own result; it never combines,
averages or compares results, and imports no framework. Built-ins are registered by direct
import (Article X: no plugins, no discovery). Synchronous throughout (Article X: no async)."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from evals.behavior import record_eval as refusal
from evals.behavior import rubric_eval
from evals.component import record_eval as component
from evals.contract import EvalRecord, EvalResult, RecordField
from evals.evaluator import EvaluatorInfo
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from trustnoagent.results import require_types, unknown_evaluator
from trustnoagent.runner import Scorer, run
from trustnoagent.version import __version__

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
    evaluator: str | RubricJudge, record: EvalRecord, judge: JudgeConfig | None = None,
    cache_dir: Path | None = None,
) -> EvalResult:
    require_types(evaluator, record)
    if isinstance(evaluator, RubricJudge):
        info = rubric_eval.rubric_info(evaluator, __version__)
        return run(partial(rubric_eval.evaluate_rubric, evaluator), info, record, judge, cache_dir)
    if (built_in := INFOS.get(evaluator)) is None:
        return unknown_evaluator(evaluator, sorted(INFOS))
    return run(REGISTRY[evaluator], built_in, record, judge, cache_dir)


def list_evaluators(*rubrics: RubricJudge) -> list[EvaluatorInfo]:
    """Built-ins sorted by id, then each rubric passed in. No credentials, env vars or network."""
    built_ins = [INFOS[key] for key in sorted(INFOS)]
    return built_ins + [rubric_eval.rubric_info(rubric, __version__) for rubric in rubrics]

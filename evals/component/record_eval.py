"""The four Ragas per-record evaluators (spec 001, US1): one caller record, one metric, one
result. Ragas only (Article II). Reuses `build_metric` — the v1 path's own constructor — and
its cached judge, so a golden-shaped record is served from the evidence v1 committed."""

from __future__ import annotations

import ragas
from ragas.metrics.base import SingleTurnMetric

from evals import outcomes
from evals.adapters.ragas_adapter import record_to_sample
from evals.cache import session
from evals.component.matrix import build_metric
from evals.component.record_failure import unusable_reply
from evals.contract import EvalRecord, EvalResult, RecordField
from evals.evaluator import EvaluatorInfo
from evals.failures import failed
from evals.fingerprint import config_fingerprint, record_hash, result_fingerprint
from evals.judge_config import JudgeConfig

LIB = f"ragas@{ragas.__version__}"
TEMPLATE_VERSION = f"{LIB}/1"  # moves only when a prompt, schema or metric class moves
# Each metric's own `_required_columns` in ragas 0.4.3, in this contract's field names.
REQUIRES: dict[str, frozenset[RecordField]] = {
    "faithfulness": frozenset({"input", "output", "contexts"}),
    "context_recall": frozenset({"input", "contexts", "expected"}),
    "context_precision": frozenset({"input", "contexts", "expected"}),
    "response_relevancy": frozenset({"input", "output"}),
}


def _score(metric: SingleTurnMetric, record: EvalRecord) -> float:
    return float(metric.single_turn_score(record_to_sample(record)))


def evaluate_ragas(
    name: str, info: EvaluatorInfo, record: EvalRecord, judge: JudgeConfig
) -> EvalResult:
    needs = REQUIRES[name]  # required fields are checked once, by the runner, for every path
    try:
        metric = build_metric(name, judge.mode)
    except ImportError as exc:  # only `response_relevancy` imports anything, and only when live
        return outcomes.error(info, f"{exc}; live {name} needs `uv sync --group calibration`")
    decoding = dict(getattr(getattr(metric, "llm", None), "model_args", {}))  # after pops
    template, schema = f"{info.id}@{TEMPLATE_VERSION}", f"{LIB}:{type(metric).__name__}"
    config = config_fingerprint(judge.judge_model, template, decoding, schema)
    fingerprint = result_fingerprint(config, record_hash(record, needs))
    with session.begin(config, f"ragas:{name}") as active:
        if judge.mode == "live":  # each attempt's real usage, queued for the entry it produces
            metric.llm.client.on("completion:response", session.push_usage)  # type: ignore[attr-defined]
        try:
            score = _score(metric, record)
        except Exception as exc:  # noqa: BLE001 — judge and fingerprint are known: keep them
            if (text := unusable_reply(exc)) is None:
                return failed(info, exc, judge.judge_model, fingerprint)
            message = f"the judge's reply could not be used ({type(exc).__name__})"
            served = dict(active.served)  # FR-033: a prior call in this metric may have written
            return outcomes.invalid(info, message, text, judge.judge_model, fingerprint, served)
        return outcomes.ok(info, score=score, judge_model=judge.judge_model,
                           fingerprint=fingerprint, served=dict(active.served))

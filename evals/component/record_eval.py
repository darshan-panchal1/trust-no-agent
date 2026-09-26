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
from evals.contract import EvalRecord, EvalResult, RecordField
from evals.evaluator import EvaluatorInfo
from evals.fingerprint import config_fingerprint, record_hash, result_fingerprint
from evals.judge_config import JudgeConfig

LIB = f"ragas@{ragas.__version__}"
TEMPLATE_VERSION = f"{LIB}/1"  # moves only when a prompt, schema or metric class moves
_ORDER: tuple[RecordField, ...] = ("input", "output", "expected", "contexts")
# Each metric's own `_required_columns` in ragas 0.4.3, in this contract's field names.
REQUIRES: dict[str, frozenset[RecordField]] = {
    "faithfulness": frozenset({"input", "output", "contexts"}),
    "context_recall": frozenset({"input", "contexts", "expected"}),
    "context_precision": frozenset({"input", "contexts", "expected"}),
    "response_relevancy": frozenset({"input", "output"}),
}


def evaluate_ragas(
    name: str, info: EvaluatorInfo, record: EvalRecord, judge: JudgeConfig
) -> EvalResult:
    needs = REQUIRES[name]
    missing = next((f for f in _ORDER if f in needs and not record.present(f)), None)
    if missing is not None:
        return outcomes.skipped(info, missing)
    metric = build_metric(name, judge.mode)
    if not isinstance(metric, SingleTurnMetric):
        raise TypeError(f"{type(metric).__name__} cannot score a single record")
    decoding = dict(getattr(getattr(metric, "llm", None), "model_args", {}))  # after pops
    schema = f"{LIB}:{type(metric).__name__}"
    template = f"{info.id}@{TEMPLATE_VERSION}"
    config = config_fingerprint(judge.judge_model, template, decoding, schema)
    with session.begin(config, f"ragas:{name}") as active:
        score = metric.single_turn_score(record_to_sample(record))
        served = dict(active.served)
    fingerprint = result_fingerprint(config, record_hash(record, needs))
    return outcomes.ok(
        info, score=score, judge_model=judge.judge_model, fingerprint=fingerprint, served=served
    )

"""`tna.deepeval.refusal_correctness` for one caller record (spec 001, US1). DeepEval only
(Article II). Built through `build_refusal_correctness_metric` — the one door (VI.a) — and
measured directly, never through `assert_test` (Article XI)."""

from __future__ import annotations

from deepeval._version import __version__ as deepeval_version
from deepeval.metrics import GEval

from evals import outcomes
from evals.adapters.deepeval_adapter import record_to_test_case
from evals.behavior.record_failure import unusable_reply
from evals.behavior.refusal import build_refusal_correctness_metric
from evals.cache import session
from evals.contract import EvalRecord, EvalResult, RecordField
from evals.evaluator import EvaluatorInfo
from evals.fingerprint import config_fingerprint, record_hash, result_fingerprint
from evals.judge.json_completion import RESPONSE_FORMAT
from evals.judge_config import JudgeConfig

LIB = f"deepeval@{deepeval_version}"  # `deepeval.__version__` is set lazily; mypy cannot see it
TEMPLATE_VERSION = "refusal-steps/1"  # bump when `evals/behavior/refusal.py`'s _STEPS change
REQUIRES: frozenset[RecordField] = frozenset({"input", "output", "expected"})
_CALL_KIND = "deepeval:refusalcorrectness"  # what `build_geval_metric` names its judge


def _measure(metric: GEval, record: EvalRecord) -> tuple[float | None, str | None]:
    metric.measure(record_to_test_case(record))
    return metric.score, metric.reason


def evaluate_refusal(info: EvaluatorInfo, record: EvalRecord, judge: JudgeConfig) -> EvalResult:
    missing = next((f for f in sorted(REQUIRES) if not record.present(f)), None)
    if missing is not None:
        return outcomes.skipped(info, missing)
    metric = build_refusal_correctness_metric(judge.mode)
    decoding = {"response_format": dict(RESPONSE_FORMAT)}
    template = f"{info.id}@{TEMPLATE_VERSION}"
    config = config_fingerprint(judge.judge_model, template, decoding, f"{LIB}:GEval")
    fingerprint = result_fingerprint(config, record_hash(record, REQUIRES))
    with session.begin(config, _CALL_KIND) as active:
        try:
            score, reason = _measure(metric, record)
        except (KeyError, ValueError) as exc:  # JSONDecodeError is a ValueError
            if (text := unusable_reply(exc, active.served)) is None:
                raise
            message = f"the judge's reply could not be used ({type(exc).__name__})"
            return outcomes.invalid(info, message, text, judge.judge_model, fingerprint)
        return outcomes.ok(info, score=score, explanation=reason, judge_model=judge.judge_model,
                           fingerprint=fingerprint, served=dict(active.served))

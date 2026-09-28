"""`EvalResult` builders (data-model.md § EvalResult). A failure never carries a score or
label, NaN never reaches a result, and a 0/0 or absent entry makes tokens unknown (FR-014/034)."""

from __future__ import annotations

import math
from collections.abc import Mapping

from evals.cache.store import CacheEntry
from evals.contract import EvalResult, RecordField
from evals.evaluator import EvaluatorInfo


def _of(info: EvaluatorInfo, **fields: object) -> EvalResult:
    return EvalResult(evaluator_id=info.id, evaluator_version=info.version, **fields)  # type: ignore[arg-type]


def _tokens(entries: list[CacheEntry]) -> tuple[int | None, int | None]:
    known = bool(entries) and all(e.input_tokens or e.output_tokens for e in entries)
    return (sum(e.input_tokens for e in entries), sum(e.output_tokens for e in entries)) \
        if known else (None, None)


def skipped(info: EvaluatorInfo, missing: RecordField) -> EvalResult:
    return _of(info, status="skipped", error=f"record has no {missing!r}, which {info.id} requires")


def error(
    info: EvaluatorInfo, message: str, judge_model: str | None = None,
    fingerprint: str | None = None, raw: Mapping[str, object] | None = None,
) -> EvalResult:
    return _of(info, status="error", error=message, judge_model=judge_model,
               judge_fingerprint=fingerprint, raw=raw or {})


def invalid(
    info: EvaluatorInfo, message: str, raw_text: str, judge_model: str | None, fingerprint: str,
    served: Mapping[str, CacheEntry] | None = None,  # FR-033: usage a completed call recorded
) -> EvalResult:
    tokens_in, tokens_out = _tokens(list((served or {}).values()))
    return _of(info, status="invalid_output", error=message, judge_model=judge_model,
               judge_fingerprint=fingerprint, raw={"responses": [raw_text]},
               tokens_in=tokens_in, tokens_out=tokens_out)


def ok(
    info: EvaluatorInfo, *, judge_model: str, fingerprint: str, served: Mapping[str, CacheEntry],
    score: float | None = None, label: str | None = None, explanation: str | None = None,
) -> EvalResult:
    keys = sorted(served)
    raw = {"cache_keys": keys, "responses": [served[k].response for k in keys]}
    if score is not None and math.isnan(score):
        return _of(info, status="invalid_output", error="judge output produced NaN",
                   judge_model=judge_model, judge_fingerprint=fingerprint, raw=raw)
    tokens_in, tokens_out = _tokens(list(served.values()))
    recorded = all(e.fingerprint is not None for e in served.values())
    provenance = ("recorded" if recorded else "not_recorded") if served else None
    return _of(info, status="ok", score=score, label=label, explanation=explanation,
               judge_model=judge_model, judge_fingerprint=fingerprint, raw=raw,
               fingerprint_provenance=provenance, tokens_in=tokens_in, tokens_out=tokens_out)

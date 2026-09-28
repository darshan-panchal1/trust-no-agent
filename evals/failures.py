"""One mapping from an exception to a result (spec FR-004), shared by the per-layer evaluators —
which know the judge and fingerprint, and pass them — and the runner's safety net, which does
not. Framework-free (Article II.c). A result carries its judge whenever the config was known."""

from __future__ import annotations

from collections.abc import Mapping

from evals import outcomes
from evals.cache.session import FingerprintMismatch
from evals.cache.store import CacheMiss
from evals.contract import EvalResult
from evals.evaluator import EvaluatorInfo

_MAX_MESSAGE = 500  # a provider's error body can be huge; a result should stay readable
_REFUSED = "; this evidence was judged under another configuration: re-score it live"


def failed(
    info: EvaluatorInfo, exc: Exception, judge_model: str | None = None,
    fingerprint: str | None = None,
) -> EvalResult:
    raw: Mapping[str, object] = {}
    if isinstance(exc, FingerprintMismatch):  # FR-030: refused, never served — kept for audit
        message = f"{exc}{_REFUSED}"
        raw = {"responses": [exc.response], "cache_keys": [exc.key]}
    elif isinstance(exc, CacheMiss):  # `record` only refreshes the built-in set: not advice here
        key = str(exc).split(" — ")[0]
        message = f"{key}: no committed evidence covers this record; score it in live mode"
    else:
        message = f"{type(exc).__name__}: {exc}"
    return outcomes.error(info, message[:_MAX_MESSAGE], judge_model, fingerprint, raw)

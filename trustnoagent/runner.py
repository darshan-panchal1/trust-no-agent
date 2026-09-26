"""Runs one resolved scorer with the FR-004 safety net: whatever it raises, the caller gets a
status. Layer-free — it never imports an eval layer, so it holds no Article II.c permission;
`evaluators.py` resolves which scorer to run, and this module runs it."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from evals import outcomes
from evals.cache import location, store
from evals.cache.store import CacheMiss
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo
from evals.judge_config import JudgeConfig
from trustnoagent.env import judge_env

Scorer = Callable[[EvaluatorInfo, EvalRecord, JudgeConfig], EvalResult]
_MAX_MESSAGE = 500  # a provider's error body can be huge; a result should stay readable
_NO_DIRECTORY = "no cache_dir given and this is not a repo checkout: pass cache_dir="
_NO_KEY = "live mode needs NVIDIA_API_KEY: export it, or pass JudgeConfig(api_key=...)"


def failure(info: EvaluatorInfo, exc: Exception) -> EvalResult:
    """A cache miss says what to do for a caller's own record — `record` only refreshes the
    built-in set, so the store's own refresh advice would be wrong here."""
    if isinstance(exc, CacheMiss):
        key = str(exc).split(" — ")[0]
        message = f"{key}: no committed evidence covers this record; score it in live mode"
    else:
        message = f"{type(exc).__name__}: {exc}"
    return outcomes.error(info, message[:_MAX_MESSAGE])


def run(
    scorer: Scorer, info: EvaluatorInfo, record: EvalRecord,
    judge: JudgeConfig | None, cache_dir: Path | None,
) -> EvalResult:
    started = time.monotonic()
    try:  # nothing a scorer raises escapes: it becomes a status (spec FR-004)
        config = judge or JudgeConfig.from_env()
        directory = cache_dir or location.default_cache_dir(store.CACHE_DIR)
        missing = next((f for f in sorted(info.requires) if not record.present(f)), None)
        if directory is None:
            result = outcomes.error(info, _NO_DIRECTORY)  # FR-032: never the wheel's own store
        elif missing is not None:  # skipped before the key: a missing field needs no credential
            result = outcomes.skipped(info, missing)
        elif config.mode == "live" and config.api_key is None:
            result = outcomes.error(info, _NO_KEY)  # FR-018: named, before any client is built
        else:  # the config, not the environment, is what every key and client reads (US5)
            with location.override(directory), judge_env(config):
                result = scorer(info, record, config)
    except Exception as exc:  # noqa: BLE001 — the point: any failure becomes a result
        result = failure(info, exc)
    raw = {**result.raw, "metadata": dict(record.metadata)} if record.metadata else result.raw
    return replace(result, raw=raw, latency_ms=round((time.monotonic() - started) * 1000))

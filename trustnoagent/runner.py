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
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo
from evals.failures import failed
from evals.judge_config import JudgeConfig
from trustnoagent.env import judge_env

Scorer = Callable[[EvaluatorInfo, EvalRecord, JudgeConfig], EvalResult]
_NO_DIRECTORY = "no cache_dir given and this is not a repo checkout: pass cache_dir="
_NO_KEY = "live mode needs NVIDIA_API_KEY: export it, or pass JudgeConfig(api_key=...)"


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
        result = failed(info, exc)  # the config may never have been reached: no judge here
    raw = {**result.raw, "metadata": dict(record.metadata)} if record.metadata else result.raw
    return replace(result, raw=raw, latency_ms=round((time.monotonic() - started) * 1000))

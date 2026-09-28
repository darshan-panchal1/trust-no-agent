"""Sets `JUDGE_MODEL`/`GENERATOR_MODEL` for one call — the two Article III accessors
(`evals.models.judge_model`/`generator_model`) require and never default. Anything outside
pytest's committed env block (Article III.a) must set them explicitly or fail. `judge_env`
does the same for a per-record `JudgeConfig`, so the config — not whatever the environment
held — is what every evidence key and every live client reads (spec 001, US5).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from evals.judge_config import JudgeConfig

_JUDGE = "JUDGE_MODEL"
_GENERATOR = "GENERATOR_MODEL"
_KEY = "NVIDIA_API_KEY"


@contextmanager
def model_env(judge_model: str, generator_model: str) -> Iterator[None]:
    """Exports both required env vars for the duration of the block, restoring whatever
    (if anything) was there before — never a process-wide, outlasting mutation."""
    previous = {name: os.environ.get(name) for name in (_JUDGE, _GENERATOR)}
    os.environ[_JUDGE] = judge_model
    os.environ[_GENERATOR] = generator_model
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextmanager
def judge_env(config: JudgeConfig) -> Iterator[None]:
    """Exports the config's models, and its key when it carries one, for exactly one call.
    Offline configs carry no key and leave the variable alone: they never build a client."""
    values = {_JUDGE: config.judge_model, _GENERATOR: config.generator_model}
    if config.api_key is not None:
        values[_KEY] = config.api_key
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

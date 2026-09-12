"""Sets `JUDGE_MODEL`/`GENERATOR_MODEL` for one call — the two Article III accessors
(`evals.models.judge_model`/`generator_model`) require and never default. Anything outside
pytest's committed env block (Article III.a) must set them explicitly or fail.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

_JUDGE = "JUDGE_MODEL"
_GENERATOR = "GENERATOR_MODEL"


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

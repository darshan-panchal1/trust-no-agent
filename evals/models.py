"""CONSTITUTION.md Article III (Eighth amendment): `JUDGE_MODEL` and `GENERATOR_MODEL`,
each read through exactly one accessor, never defaulted. A missing variable is a hard
error naming the variable — the same discipline Article III.a applies to
`DEEPEVAL_TELEMETRY_OPT_OUT`. `model_identity` in every cache key derives from these two
values, so a value declared in more than one place is a divergence waiting to happen.

Article VI.a (Tenth amendment): `NIM_BASE_URL` is the single named constant every real
client construction point uses — never an environment variable, per Article X's ban on a
provider registry, and never left to `openai.OpenAI()`'s own default of `api.openai.com`.
"""

from __future__ import annotations

import os

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _required(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise RuntimeError(
            f"{name} is not set. It is never defaulted — see CONSTITUTION.md Article III. "
            f"The offline suite sets it via pyproject.toml's [tool.pytest.ini_options] env "
            f"block; anything else (evals/cli.py, a live pass) must set it explicitly."
        )
    return value


def judge_model() -> str:
    """The Ragas and DeepEval judge's model identifier. Feeds `model_identity` for every
    `ragas:*` and `deepeval:*` cache key."""
    return _required("JUDGE_MODEL")


def generator_model() -> str:
    """The one generation model, shared by both `app` variants. Feeds `model_identity` for
    every `generate:*` cache key."""
    return _required("GENERATOR_MODEL")

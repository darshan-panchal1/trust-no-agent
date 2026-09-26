"""One judge configuration (spec FR-024–026). Models come through Article III's two required
accessors, never defaulted. The key is read only for live use and never raises here — a
missing key is a status on use. `base_url` is the Article VI.a constant, never an env var."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from evals.contract import Mode
from evals.models import NIM_BASE_URL, generator_model, judge_model


@dataclass(frozen=True)
class JudgeConfig:
    judge_model: str
    generator_model: str
    mode: Mode = "offline"
    api_key: str | None = field(default=None, repr=False)  # never printed, never logged
    base_url: str = NIM_BASE_URL

    @classmethod
    def from_env(cls, mode: Mode = "offline") -> JudgeConfig:
        return cls(
            judge_model=judge_model(),
            generator_model=generator_model(),
            mode=mode,
            api_key=os.environ.get("NVIDIA_API_KEY") if mode == "live" else None,
        )

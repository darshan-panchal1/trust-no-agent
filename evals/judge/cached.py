"""CachedJudge — the real DeepEval judge, routed through T1.4's cache accessor (Article
III). `model_identity` is `judge_model()`, read fresh each call so it can't drift. VI.a:
`_call_live`'s `openai.OpenAI()` against NIM is eager, reached only from live, never offline.
"""

from __future__ import annotations

import os
from typing import Literal

import openai
from deepeval.models import DeepEvalBaseLLM

from evals.cache.keys import hash_prompt, make_key
from evals.cache.store import CacheEntry, read_or_call, read_or_raise
from evals.judge.json_completion import json_completion
from evals.models import NIM_BASE_URL, judge_model
from evals.pricing import price_usd


class CachedJudge(DeepEvalBaseLLM):  # type: ignore[no-untyped-call]
    """One instance per metric; GEval calls `generate`/`a_generate` with a rendered prompt.
    The ignore: `__init_subclass__` calls deepeval's own untyped `observe_methods(cls)`."""

    def __init__(self, call_kind: str, mode: Literal["offline", "live"] = "offline") -> None:
        self._call_kind = call_kind
        self._mode = mode

    def get_model_name(self) -> str:
        return judge_model()

    def load_model(self) -> DeepEvalBaseLLM:
        return self

    def generate(self, prompt: str, *args: object, **kwargs: object) -> str:
        key = make_key(self._call_kind, judge_model(), hash_prompt(prompt))
        if self._mode == "offline":
            return read_or_raise(key).response
        return read_or_call(key, lambda: _call_live(self._call_kind, prompt)).response

    async def a_generate(self, prompt: str, *args: object, **kwargs: object) -> str:
        return self.generate(prompt)


def _call_live(call_kind: str, prompt: str) -> CacheEntry:
    model = judge_model()
    client = openai.OpenAI(base_url=NIM_BASE_URL, api_key=os.environ["NVIDIA_API_KEY"])
    response = json_completion(client, model, prompt)
    text = response.choices[0].message.content or ""
    usage = response.usage
    if usage is None:
        raise RuntimeError(f"NIM response for {model!r} carried no usage — cannot cost it")
    return CacheEntry(
        call_kind=call_kind,
        response=text,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        usd=price_usd(model, usage.prompt_tokens, usage.completion_tokens),
    )

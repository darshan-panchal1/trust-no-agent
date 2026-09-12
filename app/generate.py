"""Mode-gated generation — the sole `generate:*` caller of the cache accessor.

Article III: offline reads only, raises on a miss; live calls, records, writes.
"""

from __future__ import annotations

import os
from typing import Literal

import openai

from evals.cache.keys import hash_prompt, make_key
from evals.cache.store import CacheEntry, read_or_call, read_or_raise
from evals.models import NIM_BASE_URL, generator_model
from evals.pricing import price_usd


def generate(
    variant: str,
    system_prompt: str,
    user_prompt: str,
    mode: Literal["offline", "live"] = "offline",
    client: openai.OpenAI | None = None,
) -> str:
    """Return the generated answer text. Offline by default; `mode="live"` is explicit."""
    model = generator_model()
    rendered = f"{system_prompt}\n\n{user_prompt}"
    key = make_key(f"generate:{variant}", model, hash_prompt(rendered))
    if mode == "offline":
        return read_or_raise(key).response
    if client is None:
        client = openai.OpenAI(base_url=NIM_BASE_URL, api_key=os.environ["NVIDIA_API_KEY"])
    entry = read_or_call(
        key, lambda: _call_live(variant, client, model, system_prompt, user_prompt)
    )
    return entry.response


def _call_live(
    variant: str, client: openai.OpenAI, model: str, system_prompt: str, user_prompt: str
) -> CacheEntry:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content or ""
    usage = response.usage
    if usage is None:
        raise RuntimeError(f"NIM response for {model!r} carried no usage — cannot cost it")
    return CacheEntry(
        call_kind=f"generate:{variant}",
        response=text,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        usd=price_usd(model, usage.prompt_tokens, usage.completion_tokens),
    )

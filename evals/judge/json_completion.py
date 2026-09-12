"""Trap 30 (docs/api-notes.md): NIM's `json_object` mode still let a reasoning-heavy judge
emit one valid JSON object, then echo a prompt fragment and restart it a second time —
grammar-constrained decoding narrowed but did not eliminate the failure. One retry, verified
live against the actual failing case.
"""

from __future__ import annotations

import json

import openai
from openai.types.chat import ChatCompletion

_MAX_ATTEMPTS = 2


def json_completion(client: openai.OpenAI, model: str, prompt: str) -> ChatCompletion:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        try:
            json.loads(response.choices[0].message.content or "")
            return response
        except json.JSONDecodeError:
            if attempt == _MAX_ATTEMPTS:
                raise
    raise AssertionError("unreachable: loop always returns or raises on final attempt")

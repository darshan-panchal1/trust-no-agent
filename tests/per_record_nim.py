"""A socket-free stand-in for NIM, for live-mode tests — not collected (no `test_` prefix).

`MockNim` builds a *real* `openai.OpenAI` whose transport never opens a socket, so live-mode
code paths run offline under `socket_disabled`. Install it with `install(monkeypatch, mock)`,
never by replacing `openai.OpenAI` itself: instructor does `isinstance(client, openai.OpenAI)`,
which raises if that name is no longer a class."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace

import httpx
import openai
import pytest

import app.generate
import evals.judge.cached
import evals.ragas_llm

_REAL_OPENAI = openai.OpenAI


class MockNim:
    """Stands in for `openai.OpenAI(...)`; `calls` counts HTTP requests actually served."""

    def __init__(self, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        self._handler = handler
        self.calls = 0

    def _serve(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return self._handler(request)

    def __call__(self, *, base_url: str, api_key: str) -> openai.OpenAI:
        """The exact keywords all three NIM construction points pass (Article VI.a)."""
        transport = httpx.MockTransport(self._serve)
        client = httpx.Client(transport=transport)
        return _REAL_OPENAI(base_url=base_url, api_key=api_key, http_client=client)


def install(monkeypatch: pytest.MonkeyPatch, mock: MockNim) -> None:
    """Swap the `openai` name inside each NIM construction point (Article VI.a lists three)
    for a namespace whose `OpenAI` is the mock. The real `openai.OpenAI` class is untouched."""
    shim = SimpleNamespace(OpenAI=mock)
    for module in (evals.ragas_llm, evals.judge.cached, app.generate):
        monkeypatch.setattr(module, "openai", shim)


def chat(content: str) -> Callable[[httpx.Request], httpx.Response]:
    """A handler replying with one plain chat completion (5 prompt / 2 completion tokens)."""
    body = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}}
    return lambda _request: httpx.Response(200, json=body)

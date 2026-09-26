"""Shared helpers for the per-record tests — not collected (no `test_` prefix). Imports
neither eval layer (Article II.c): records come from the app, judging from the facade.

`MockNim` builds a *real* `openai.OpenAI` whose transport never opens a socket, so live-mode
code paths run offline under `socket_disabled`. Install it with
`monkeypatch.setattr(openai, "OpenAI", mock)` — it keeps the real class captured at import,
so it never recurses into its own patch."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import openai

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.contract import EvalRecord
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase

_REAL_OPENAI = openai.OpenAI
_VARIANTS: dict[str, Callable[..., AgentResult]] = {"v1_naive": v1_answer, "v2_fixed": v2_answer}


def golden_record(variant: str, index: int) -> tuple[GoldenCase, EvalRecord]:
    """One committed golden case and its offline answer, as a caller would supply them."""
    case = load_golden()[index]
    result = _VARIANTS[variant](case.question, mode="offline")
    record = EvalRecord(
        input=case.question,
        output=result.answer,
        expected=case.ground_truth,
        contexts=tuple(chunk.text for chunk in result.retrieved_contexts),
    )
    return case, record


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

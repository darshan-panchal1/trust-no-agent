"""One judge `InstructorLLM` per Ragas metric, cached through the Trap 19 re-key fix.

Offline: a stub client, never a real `openai.OpenAI()` — VI.a forbids constructing a real
NIM client on any offline path. Live mode goes through `instructor.from_openai()` against
NIM's `base_url`; `provider="openai"` is correct since the client genuinely is one.

`InstructorModelArgs()`'s defaults carry `temperature=0.01`/`top_p=0.1` (Article III bans
both, fixed on the constructed `InstructorLLM`, not the args) and `max_tokens=1024` — measured
too low; 4096 and 16000 also still truncated, on Faithfulness's NLI verdict step specifically,
not the statement-generator step a smaller probe had checked. 32000 is the first value verified
against a full two-variant live pass end to end, zero truncations — a working floor, not a
proven ceiling (docs/api-notes.md Trap 27). Headroom costs nothing extra: NIM bills actual
completion tokens, not the ceiling.
"""

from __future__ import annotations

import os
from typing import Literal

import instructor
import openai
from ragas.llms.base import InstructorLLM, InstructorModelArgs

from evals.cache.ragas_backend import RagasCacheBackend
from evals.models import NIM_BASE_URL, judge_model


class _NeverCalledCompletions:
    def create(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("offline InstructorLLM must never reach the real client")


class _NeverCalledChat:
    completions = _NeverCalledCompletions()


class _NeverCalledClient:
    """Same duck-typed shape `InstructorLLM._check_client_async` inspects
    (`.chat.completions.create`) — nothing else touches this object offline."""

    chat = _NeverCalledChat()


def build_judge_llm(
    metric_name: str, mode: Literal["offline", "live"] = "offline"
) -> InstructorLLM:
    """Build the judge LLM for one Ragas metric, cached under `ragas:<metric_name>`."""
    model = judge_model()
    cache = RagasCacheBackend(f"ragas:{metric_name}", model, mode=mode)
    client: object = _NeverCalledClient()
    if mode == "live":
        # only ever constructed here — VI.a
        real_client = openai.OpenAI(base_url=NIM_BASE_URL, api_key=os.environ["NVIDIA_API_KEY"])
        client = instructor.from_openai(real_client)
    args = InstructorModelArgs(max_tokens=32000)
    llm = InstructorLLM(client=client, model=model, provider="openai", model_args=args, cache=cache)
    llm.model_args.pop("temperature", None)  # Article III — banned everywhere, not sent
    llm.model_args.pop("top_p", None)
    return llm

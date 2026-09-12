"""The regressed v2 used by `evals/ops/regression_demo.py`, and nowhere else.

Identical to `app/v2_fixed` on every axis Article IV names — the retrieval constants are
imported from it rather than copied, so they cannot drift — except the system prompt, which
drops v2's context-only clause and licenses a general-knowledge fallback instead. That is the
whole regression, and it reads as a product improvement: stop answering "I don't know" when
general knowledge would help.

Measured first, not assumed: merely *omitting* v2's refusal instruction was not enough — all
five out-of-scope cases still refused correctly. The fabrication needs the fallback to be
*licensed*, which is the clause `app/v1_naive`'s prompt has and this one reinstates.

Deliberately not in `app/`: this is demo scaffolding, not a third shipped variant. Article
IV's table describes v1 against v2 and stays exhaustive.
"""

from __future__ import annotations

import time
from typing import Literal

from app.context import build_context
from app.generate import generate
from app.models import AgentResult
from app.prompts import build_user_prompt
from app.rerank import rerank
from app.tool_calling import decide_tool_calls
from app.v2_fixed import CHUNK_SIZE, OVERLAP, TOP_K

VARIANT = "regression_demo:v2_regressed"  # namespaces every cache entry this variant writes

REGRESSED_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about Meridian Logistics company policy. "
    "Use the provided context below, and supplement it with your general knowledge of standard "
    "company policy where the context is incomplete. Answer confidently and directly."
)


def answer(question: str, mode: Literal["offline", "live"] = "offline") -> AgentResult:
    start = time.monotonic()
    contexts = build_context(question, CHUNK_SIZE, OVERLAP, TOP_K, rerank_fn=rerank)
    tool_calls = decide_tool_calls(question, contexts, inject_spurious=False)
    user_prompt = build_user_prompt(question, contexts)
    text = generate(VARIANT, REGRESSED_SYSTEM_PROMPT, user_prompt, mode=mode)
    latency_ms = (time.monotonic() - start) * 1000
    return AgentResult(
        answer=text, retrieved_contexts=contexts, tool_calls=tool_calls, latency_ms=latency_ms
    )

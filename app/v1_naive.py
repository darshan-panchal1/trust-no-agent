"""v1_naive — deliberately degraded: narrow retrieval, no rerank, permissive prompt,
spurious tool calls on multi-hop questions.

CONSTITUTION.md Article IV: this variant is never fixed. Its flaws are the subject of the
tutorial, not a bug in the backlog.
"""

from __future__ import annotations

import time
from typing import Literal

from app.context import build_context
from app.generate import generate
from app.models import AgentResult
from app.prompts import V1_SYSTEM_PROMPT, build_user_prompt
from app.tool_calling import decide_tool_calls

CHUNK_SIZE = 200
OVERLAP = 0
TOP_K = 2


def answer(question: str, mode: Literal["offline", "live"] = "offline") -> AgentResult:
    start = time.monotonic()
    contexts = build_context(question, CHUNK_SIZE, OVERLAP, TOP_K)
    tool_calls = decide_tool_calls(question, contexts, inject_spurious=True)
    user_prompt = build_user_prompt(question, contexts)
    text = generate("v1_naive", V1_SYSTEM_PROMPT, user_prompt, mode=mode)
    latency_ms = (time.monotonic() - start) * 1000
    return AgentResult(
        answer=text, retrieved_contexts=contexts, tool_calls=tool_calls, latency_ms=latency_ms
    )

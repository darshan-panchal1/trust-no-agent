"""v2_fixed — corrected: wide retrieval with overlap and rerank, strict citation-required
prompt, calls only the tools it needs.
"""

from __future__ import annotations

import time
from typing import Literal

from app.context import build_context
from app.generate import generate
from app.models import AgentResult
from app.prompts import V2_SYSTEM_PROMPT, build_user_prompt
from app.rerank import rerank
from app.tool_calling import decide_tool_calls

CHUNK_SIZE = 800
OVERLAP = 200
TOP_K = 5


def answer(question: str, mode: Literal["offline", "live"] = "offline") -> AgentResult:
    start = time.monotonic()
    contexts = build_context(question, CHUNK_SIZE, OVERLAP, TOP_K, rerank_fn=rerank)
    tool_calls = decide_tool_calls(question, contexts, inject_spurious=False)
    user_prompt = build_user_prompt(question, contexts)
    text = generate("v2_fixed", V2_SYSTEM_PROMPT, user_prompt, mode=mode)
    latency_ms = (time.monotonic() - start) * 1000
    return AgentResult(
        answer=text, retrieved_contexts=contexts, tool_calls=tool_calls, latency_ms=latency_ms
    )

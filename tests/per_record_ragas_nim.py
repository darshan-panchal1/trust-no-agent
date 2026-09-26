"""A socket-free NIM that answers Faithfulness's two structured calls — not collected. Probed on
the pinned ragas 0.4.3: instructor TOOLS mode, forced `tool_choice` naming the response model,
first `StatementGeneratorOutput`, then `NLIStatementOutput`. Each tool gets its own usage, so a
test can tell which call's tokens landed on which evidence entry."""

from __future__ import annotations

import json

import httpx

STATEMENTS = {"statements": ["The sky is blue."]}
VERDICTS = {"statements": [{"statement": "The sky is blue.", "reason": "stated", "verdict": 1}]}
USAGE = {"StatementGeneratorOutput": (123, 45), "NLIStatementOutput": (200, 60)}
REPLIES = {"StatementGeneratorOutput": STATEMENTS, "NLIStatementOutput": VERDICTS}


def tool_reply(tool: str, arguments: object, usage: tuple[int, int]) -> httpx.Response:
    prompt, completion = usage
    call = {"id": "t", "type": "function",
            "function": {"name": tool, "arguments": json.dumps(arguments)}}
    body = {"id": "x", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "tool_calls",
                         "message": {"role": "assistant", "content": None, "tool_calls": [call]}}],
            "usage": {"prompt_tokens": prompt, "completion_tokens": completion,
                      "total_tokens": prompt + completion}}
    return httpx.Response(200, json=body)


def requested_tool(request: httpx.Request) -> str:
    return str(json.loads(request.content)["tool_choice"]["function"]["name"])


def faithfulness(request: httpx.Request) -> httpx.Response:
    """Answer each call correctly, with that call's own usage."""
    tool = requested_tool(request)
    return tool_reply(tool, REPLIES[tool], USAGE[tool])

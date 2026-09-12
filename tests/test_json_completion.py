"""Trap 30: NIM's `json_object` mode narrowed but did not eliminate a judge emitting one
valid JSON object then restarting it — one retry on a malformed response."""

from __future__ import annotations

import json

import pytest

from evals.judge.json_completion import json_completion


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.calls = 0

    def create(self, **kwargs: object) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self._replies.pop(0))


class _FakeChat:
    def __init__(self, replies: list[str]) -> None:
        self.completions = _FakeCompletions(replies)


class _FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self.chat = _FakeChat(replies)


def test_a_malformed_reply_is_retried_once_and_the_good_reply_wins() -> None:
    self_repeated = '{"score": 0}\n\nMake sure no\n\n{"score": 0}'
    client = _FakeClient([self_repeated, '{"score": 0}'])
    response = json_completion(client, "some-model", "prompt")  # type: ignore[arg-type]
    assert response.choices[0].message.content == '{"score": 0}'
    assert client.chat.completions.calls == 2


def test_two_malformed_replies_in_a_row_raises() -> None:
    client = _FakeClient(["not json", "still not json"])
    with pytest.raises(json.JSONDecodeError):
        json_completion(client, "some-model", "prompt")  # type: ignore[arg-type]

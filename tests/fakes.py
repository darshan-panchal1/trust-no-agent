"""Shared test doubles — not collected by pytest (no `test_` prefix)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass
class FakeMessage:
    content: str


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeChatCompletion:
    choices: list[FakeChoice]
    usage: FakeUsage


class FakeCompletionsResource:
    def create(self, **_kwargs: object) -> FakeChatCompletion:
        return FakeChatCompletion(
            choices=[FakeChoice(message=FakeMessage(content="stub answer"))],
            usage=FakeUsage(prompt_tokens=10, completion_tokens=5),
        )


class FakeChatResource:
    completions = FakeCompletionsResource()


class FakeClient:
    chat = FakeChatResource()

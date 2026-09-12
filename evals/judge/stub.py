"""Offline stub judge (Article VI.a): passed to metrics that must never actually call a
model, so a stray call becomes a loud test failure instead of a silent live request.
"""

from __future__ import annotations

from deepeval.models import DeepEvalBaseLLM

_NEVER_CALLED = "stub judge invoked — this metric is supposed to be fully deterministic"


class StubJudge(DeepEvalBaseLLM):  # type: ignore[no-untyped-call]
    # DeepEvalBaseLLM.__init_subclass__ calls deepeval's own untyped observe_methods(cls).
    def get_model_name(self) -> str:
        return "stub-judge"

    def load_model(self) -> DeepEvalBaseLLM:
        return self

    def generate(self, *args: object, **kwargs: object) -> str:
        raise AssertionError(_NEVER_CALLED)

    async def a_generate(self, *args: object, **kwargs: object) -> str:
        raise AssertionError(_NEVER_CALLED)

"""T2.2 acceptance: every metric's judge LLM stays off the event loop offline.

The real `openai.OpenAI()`'s own sync-ness is a property of the SDK itself, not something
this repo verifies — VI.a forbids constructing a real NIM client on any offline test path
regardless. This test instead proves the *offline stub* carries the same duck-typed shape
`InstructorLLM` inspects to decide sync vs. async, so nothing here could route through the
event loop.
"""

from __future__ import annotations

from evals.ragas_llm import build_judge_llm


def test_build_judge_llm_is_sync_offline() -> None:
    llm = build_judge_llm("faithfulness")
    assert llm.is_async is False


def test_build_judge_llm_never_carries_a_sampling_parameter() -> None:
    """Trap 27 (docs/api-notes.md): `InstructorModelArgs()`'s own defaults
    (`temperature=0.01`, `top_p=0.1`) were spread unchecked into every live call — a live
    Article III violation, caught only by reading `InstructorLLM`'s source. Regression: these
    two keys must never be present in `model_args` again, for any provider that comes next."""
    llm = build_judge_llm("faithfulness")
    assert "temperature" not in llm.model_args
    assert "top_p" not in llm.model_args

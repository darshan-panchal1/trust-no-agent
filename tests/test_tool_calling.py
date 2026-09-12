"""T1.8 acceptance: v1's spurious tool calls are independent of retrieval outcome (FR-005)."""

from __future__ import annotations

from app.models import RetrievedChunk
from app.tool_calling import SPURIOUS_TERMS, decide_tool_calls, looks_multi_hop

MULTI_HOP_QUESTION = "Can a Senior Manager approve their own international travel trip?"


def test_question_is_classified_multi_hop() -> None:
    assert looks_multi_hop(MULTI_HOP_QUESTION) is True


def test_spurious_call_set_identical_regardless_of_retrieval_outcome() -> None:
    successful_contexts = [
        RetrievedChunk(text="travel content", source_document="travel.md", score=5.0),
        RetrievedChunk(text="procurement content", source_document="procurement.md", score=4.0),
    ]
    failed_contexts: list[RetrievedChunk] = []  # retrieval returned nothing useful

    calls_success = decide_tool_calls(
        MULTI_HOP_QUESTION, successful_contexts, inject_spurious=True
    )
    calls_failed = decide_tool_calls(MULTI_HOP_QUESTION, failed_contexts, inject_spurious=True)

    spurious_success = [c for c in calls_success if c.name == "lookup_glossary"]
    spurious_failed = [c for c in calls_failed if c.name == "lookup_glossary"]

    assert spurious_success == spurious_failed
    assert [c.arguments["term"] for c in spurious_success] == SPURIOUS_TERMS


def test_v2_never_injects_spurious_calls() -> None:
    contexts = [RetrievedChunk(text="x", source_document="travel.md", score=1.0)]
    calls = decide_tool_calls(MULTI_HOP_QUESTION, contexts, inject_spurious=False)
    assert not any(c.name == "lookup_glossary" for c in calls)


def test_non_multi_hop_question_gets_no_tool_calls() -> None:
    contexts = [RetrievedChunk(text="x", source_document="pto.md", score=1.0)]
    calls = decide_tool_calls("How many PTO days do I get?", contexts, inject_spurious=True)
    assert calls == []

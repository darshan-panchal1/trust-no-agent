"""T2.4 acceptance: Article II.b boundary, and correct fields with no raw filenames."""

from __future__ import annotations

from pathlib import Path

from app.models import AgentResult, RetrievedChunk
from evals.adapters.ragas_adapter import to_single_turn_sample
from evals.golden.load import load_golden


def test_adapter_module_has_no_deepeval_import() -> None:
    source = Path("evals/adapters/ragas_adapter.py").read_text()
    assert "import deepeval" not in source
    assert "from deepeval" not in source


def test_adapter_builds_correct_fields_with_no_raw_filenames() -> None:
    case = load_golden()[0]
    chunk = RetrievedChunk(
        text="badges are issued same-day", source_document="badge-access.md", score=1.0
    )
    result = AgentResult(
        answer="answer text", retrieved_contexts=[chunk], tool_calls=[], latency_ms=1.0
    )
    sample = to_single_turn_sample(case, result)
    assert sample.user_input == case.question
    assert sample.reference == case.ground_truth
    assert sample.response == "answer text"
    assert sample.retrieved_contexts == ["badges are issued same-day"]
    assert "badge-access.md" not in sample.retrieved_contexts[0]

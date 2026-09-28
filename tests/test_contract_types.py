"""T005: the framework-free contract types (data-model.md) — frozen, plain, and equal on
everything but the latency they measured."""

from __future__ import annotations

import dataclasses
from typing import get_args

import pytest

from evals.contract import (
    EvalRecord,
    EvalResult,
    Mode,
    OutputType,
    Provenance,
    RecordField,
    Status,
)
from tests.repo_files import REPO_ROOT
from tests.source_ast import imported_modules


def test_a_record_is_frozen_and_every_field_is_optional() -> None:
    record = EvalRecord()
    assert (record.input, record.output, record.expected, record.contexts) == (None,) * 4
    assert record.metadata == {}
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.input = "changed"  # type: ignore[misc]


def test_empty_is_present_and_only_none_is_absent() -> None:
    """Spec edge case: `contexts=()` or `output=""` is scored, never skipped."""
    record = EvalRecord(output="", contexts=())
    assert record.present("output") and record.present("contexts")
    assert not record.present("input")


def test_result_equality_ignores_the_measured_latency() -> None:
    """SC-005: a cached re-run is identical in every field except the time it took."""
    first = EvalResult(evaluator_id="tna.x", evaluator_version="v", status="ok", latency_ms=1)
    assert first == dataclasses.replace(first, latency_ms=99)
    assert first != dataclasses.replace(first, status="error")


def test_the_literal_vocabularies_are_exactly_the_documented_ones() -> None:
    assert get_args(Status) == ("ok", "error", "skipped", "invalid_output")
    assert get_args(OutputType) == ("score", "label", "bool")
    assert get_args(Provenance) == ("recorded", "not_recorded")
    assert get_args(RecordField) == ("input", "output", "expected", "contexts")


def test_mode_has_one_definition_that_the_v1_surface_reuses() -> None:
    """`Literal[...]` is cached by typing, so `is` alone would pass for two copies — the
    import edge is what proves there is one."""
    import trustnoagent

    assert get_args(trustnoagent.Mode) == get_args(Mode) == ("offline", "live")
    assert "evals.contract" in imported_modules(REPO_ROOT / "trustnoagent" / "suite.py")

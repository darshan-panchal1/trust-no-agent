"""T1.2 acceptance: 25 cases load; malformed cases raise at load (FR-012)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.golden.load import load_golden


def test_all_25_cases_load() -> None:
    assert len(load_golden()) == 25


def test_multi_hop_missing_expected_tools_raises(tmp_path: Path) -> None:
    bad_case = {
        "question": "q",
        "ground_truth": "gt",
        "reference_contexts": [],
        "category": "multi-hop",
    }
    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(json.dumps(bad_case) + "\n")
    with pytest.raises(ValidationError, match="expected_tools"):
        load_golden(path=bad_path)


def test_reference_contexts_naming_unknown_file_raises(tmp_path: Path) -> None:
    bad_case = {
        "question": "q",
        "ground_truth": "gt",
        "reference_contexts": ["does-not-exist.md"],
        "category": "answerable",
    }
    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(json.dumps(bad_case) + "\n")
    with pytest.raises(ValueError, match="unknown corpus files"):
        load_golden(path=bad_path)

"""Article V: thresholds are versioned data. FR-043 compare reads its tolerance from this file."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from evals import thresholds
from evals.ops.compare import compare_runs
from evals.ops.run_summary import MetricRow, RunSummary

FIXTURE = """
comparison_tolerance: 0.02
comparison_tolerance_justification: test fixture value
metrics:
  faithfulness:
    value: 0.65
    justification: midpoint of the observed v1/v2 gap
    v1_observed: 0.41
    v2_observed: 0.88
"""


@pytest.fixture
def thresholds_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "thresholds.yaml"
    path.write_text(FIXTURE)
    monkeypatch.setattr(thresholds, "THRESHOLDS_PATH", path)
    return path


def _summary(v2_mean: float) -> RunSummary:
    return RunSummary(
        generated_at=datetime.datetime(2026, 9, 7, 12, 0, tzinfo=datetime.UTC),
        metrics=[MetricRow(metric="faithfulness", v1_mean=0.41, v2_mean=v2_mean, threshold=0.65)],
        worst_regressions=[],
        costs=[],
    )


def test_a_missing_thresholds_file_names_the_command_that_writes_it() -> None:
    with pytest.raises(FileNotFoundError, match="calibrate"):
        thresholds.load_thresholds(Path("/nonexistent/thresholds.yaml"))


def test_a_missing_metric_is_a_loud_error_not_a_default(thresholds_file: Path) -> None:
    assert thresholds.threshold_for("faithfulness") == 0.65
    with pytest.raises(KeyError, match="context_recall"):
        thresholds.threshold_for("context_recall")


def test_compare_reads_its_tolerance_from_the_same_file(
    thresholds_file: Path, tmp_path: Path
) -> None:
    baseline, candidate = tmp_path / "base.json", tmp_path / "cand.json"
    _summary(0.88).save(baseline)
    _summary(0.80).save(candidate)
    assert [item.metric for item in compare_runs(baseline, candidate)] == ["faithfulness"]

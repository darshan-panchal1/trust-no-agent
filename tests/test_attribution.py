"""Article IV's second enforcement: `docs/attribution.md` names exactly the metrics the
separation contract gates on, one axis each — so the doc cannot drift from the code that
decides what actually gates a pass (`evals/gate_policy.GATED_METRICS`).
"""

from __future__ import annotations

import re

from evals.gate_policy import GATED_METRICS
from tests.repo_files import REPO_ROOT

ATTRIBUTION = REPO_ROOT / "docs" / "attribution.md"
AXES = {"retrieval", "prompt", "tool"}
SEPARATING = "separating gate"
_ROW = re.compile(r"^\|\s*`(\w+)`\s*\|\s*([\w ]+?)\s*\|\s*([\w ]+?)\s*\|$", re.MULTILINE)


def _rows() -> list[tuple[str, str, str]]:
    """`(metric, axis, role)` per table row — the backticks on the metric name are what
    keep the header and separator rows out without hand-parsing the table shape."""
    return _ROW.findall(ATTRIBUTION.read_text())


def test_the_file_names_exactly_the_metrics_that_separate() -> None:
    separating = {metric for metric, _, role in _rows() if role == SEPARATING}
    assert separating == set(GATED_METRICS)


def test_every_metric_is_attributed_to_exactly_one_known_axis() -> None:
    rows = _rows()
    metrics = [metric for metric, _, _ in rows]
    assert len(metrics) == len(set(metrics)), f"a metric is listed twice: {metrics}"
    assert {axis for _, axis, _ in rows} <= AXES


def test_tool_correctness_is_listed_and_is_not_a_gate() -> None:
    """Article II.a: demonstrative only. Listed so the table stays exhaustive over the
    three axes, but it must never appear as a gate."""
    roles = {metric: role for metric, _, role in _rows()}
    assert roles["ToolCorrectness"] == "demonstrative only"


def test_the_file_states_that_attribution_is_not_experimental() -> None:
    """Article IV requires this caveat in the file's own text, not only in the constitution."""
    text = ATTRIBUTION.read_text()
    assert "asserted by construction, not proven by experiment" in text
    assert "2x2" in text or "2×2" in text

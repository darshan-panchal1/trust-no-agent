"""T4.3 acceptance: both renderings are generated and their score matrices agree — the
check compares rendered figures, not template source (FR-042)."""

from __future__ import annotations

import datetime
from pathlib import Path

from evals.cost import CostRow
from evals.ops.report import HTML_TEMPLATE, MARKDOWN_TEMPLATE, render, write_reports
from evals.ops.run_summary import MetricRow, Regression, RunSummary

ANSWER = "The per diem rate is $95 per day, which applies to all destinations."


def _summary() -> RunSummary:
    return RunSummary(
        generated_at=datetime.datetime(2026, 9, 7, 12, 0, tzinfo=datetime.UTC),
        metrics=[
            MetricRow(metric="faithfulness", v1_mean=0.412, v2_mean=0.883, threshold=0.650),
            MetricRow(metric="context_recall", v1_mean=0.500, v2_mean=0.910, threshold=0.700),
        ],
        worst_regressions=[
            Regression(
                metric="faithfulness",
                question="What is the current per diem rate?",
                variant="v1_naive",
                score=0.12,
                answer=ANSWER,
            )
        ],
        costs=[
            CostRow(
                call_kind="ragas:faithfulness", calls=50, cached=50,
                input_tokens=41203, output_tokens=3110, usd=0.0,
            )
        ],
    )


def test_both_renderings_are_written(tmp_path: Path) -> None:
    markdown_path, html_path = write_reports(_summary(), tmp_path)
    assert markdown_path.exists() and html_path.exists()
    assert markdown_path.suffix == ".md" and html_path.suffix == ".html"


def test_score_matrix_sections_agree() -> None:
    summary = _summary()
    markdown, html = render(summary, MARKDOWN_TEMPLATE), render(summary, HTML_TEMPLATE)
    for row in summary.metrics:
        for figure in (f"{row.v1_mean:.3f}", f"{row.v2_mean:.3f}", f"{row.delta:+.3f}"):
            assert figure in markdown, figure
            assert figure in html, figure


def test_the_answer_text_survives_into_both_renderings() -> None:
    """FR-042: the answer is the load-bearing part of a regression entry."""
    summary = _summary()
    assert ANSWER in render(summary, MARKDOWN_TEMPLATE)
    assert ANSWER in render(summary, HTML_TEMPLATE)

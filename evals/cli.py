"""Article I.a: the only module importing typer (a test node running these corrupts thresholds)."""

from __future__ import annotations

from pathlib import Path

import typer

from evals.cost_table import format_cost_table
from evals.ops.calibrate import calibrate as run_calibration
from evals.ops.compare import compare_runs
from evals.ops.coverage import coverage
from evals.ops.record import record as record_evidence
from evals.ops.report import write_reports
from evals.ops.run_summary import RunSummary
from evals.ops.summary import write_summary
from trustnoagent import run_gate

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False, help="Operator commands.")
SUMMARY_PATH = Path("evals/reports") / "summary.json"  # FR-042/048: report/compare's input

@app.command()
def record(usd_ceiling: float = 5.0, dry_run: bool = False, allow_unpriced: bool = False) -> None:
    """Create or refresh evidence entries — the only command that ever writes them."""
    for row in coverage():
        typer.echo(f"{row.call_kind:<32}{row.present:>5} /{row.expected:>5}  missing {row.missing}")
    missing = record_evidence(usd_ceiling, dry_run, allow_unpriced)
    typer.echo(f"{'dry run: ' if dry_run else ''}{missing} entries missing")
    if not dry_run:
        write_summary(SUMMARY_PATH)
        typer.echo(f"wrote {SUMMARY_PATH}")

@app.command()
def calibrate() -> None:
    """Write `thresholds.yaml` from committed evidence (FR-039). Offline, never billed."""
    run_calibration()
    typer.echo("wrote evals/thresholds.yaml")

@app.command()
def compare(baseline: Path, candidate: Path) -> None:
    """Exit non-zero if `candidate` regressed against `baseline` beyond tolerance."""
    regressed = compare_runs(baseline, candidate)
    for item in regressed:
        typer.echo(f"REGRESSED {item.metric}: {item.baseline:.3f} -> {item.candidate:.3f}")
    raise typer.Exit(code=1 if regressed else 0)

@app.command()
def report(summary: Path, out_dir: Path = Path("evals/reports")) -> None:
    """Render one run summary as both Markdown and HTML (FR-042)."""
    loaded = RunSummary.load(summary)
    markdown_path, html_path = write_reports(loaded, out_dir)
    typer.echo(f"{format_cost_table(loaded.costs)}\nwrote {markdown_path}\nwrote {html_path}")

@app.command()
def gate(judge_model: str, generator_model: str) -> None:
    """Exit non-zero on a gated-metric miss (Article IV); offline only, per Article VI."""
    raise typer.Exit(code=run_gate(judge_model, generator_model, None, "offline"))

if __name__ == "__main__":  # Article I carves out this module by name for exactly this.
    app()

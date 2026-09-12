"""The public entry point. `EvalSuite` wraps `evals.ops.*` with no new eval logic — judge
and generator model selection (Article III, no defaults), dataset input, and mode become
constructor arguments instead of pytest's committed env block or module constants.

Does not expose (Articles V, X): providers, `base_url`, threshold overrides, metric
registration, cache backends, async. `judge_model`/`generator_model` are model IDs within
one provider — the env-var selection Article X blesses, not a provider abstraction layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase
from evals.ops.report import write_reports
from evals.ops.run_summary import RunSummary
from evals.ops.summary import build_summary
from trustnoagent.env import model_env
from trustnoagent.gate import failing_metrics

Mode = Literal["offline", "live"]


class EvalSuite:
    """Runs the same evaluation `evals.cli record` does, against caller-chosen models and
    dataset. `mode="live"` reaches generation only — see `evals.ops.summary.build_summary`."""

    def __init__(
        self,
        judge_model: str,
        generator_model: str,
        dataset: Path | None = None,
        mode: Mode = "offline",
    ) -> None:
        self.judge_model = judge_model
        self.generator_model = generator_model
        self.cases: list[GoldenCase] = load_golden() if dataset is None else load_golden(dataset)
        self.mode = mode

    def run(self) -> RunSummary:
        with model_env(self.judge_model, self.generator_model):
            return build_summary(cases=self.cases, mode=self.mode)

    def gate(self, summary: RunSummary) -> list[str]:
        """Gated metric names that miss Article IV's calibrated bar. Empty means all held."""
        return failing_metrics(summary)

    def report(self, summary: RunSummary, out_dir: Path) -> tuple[Path, Path]:
        """Render `summary` as Markdown and HTML; returns both paths."""
        return write_reports(summary, out_dir)


def run_gate(judge_model: str, generator_model: str, dataset: Path | None, mode: Mode) -> int:
    """`evals.cli gate`'s entire body — kept out of the typer-only module (Article I.a)."""
    failed = failing_metrics(EvalSuite(judge_model, generator_model, dataset, mode).run())
    for name in failed:
        print(f"GATE FAILED {name}")
    return 1 if failed else 0

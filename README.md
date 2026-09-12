# trust-no-agent

An LLM-agent evaluation harness that proves an agent is broken even when its outputs look
fine.

Two variants of the same document-QA agent ship here. They are indistinguishable by reading
their answers — both are fluent, confident and well written. One of them is measurably
wrong, and the point of this repository is that you cannot tell which without the harness.

```
git clone <repo> && cd trust-no-agent && uv sync && uv run pytest
```

That is the whole thing. No API key, no configuration, no network: every judge call is
served from committed evidence under `evals/.judge_cache/`, and the run ends with a cost
table showing `$0.00`. Expect `3 xfailed` in the summary — those are v1 measured against
the real calibrated thresholds (`tests/test_separation_contract.py`) and failing every one,
marked expected because v1 is never fixed. That is the point of the repository, not a bug
in the suite.

## What you are looking at

| | |
|---|---|
| `app/v1_naive` · `app/v2_fixed` | the two variants — same corpus, same model, three deliberate differences |
| `evals/component/` | Ragas metrics — *why* is it bad? (scalar diagnostics) |
| `evals/behavior/` | DeepEval checks — pass/fail verdicts, but scored against GEval's library default (`threshold=0.5`), not the calibrated bars |
| `evals/thresholds.yaml` | the real gate: thresholds calibrated from v1/v2's actual scored runs |
| `tests/test_separation_contract.py` | the only test that reads the calibrated thresholds — v1 must miss every bar, v2 must clear all three |
| `evals/.judge_cache/` | the committed evidence, one reviewable JSON per call |
| `tests/test_harness_integrity.py` | proof the harness itself can lie, and does |
| `docs/attribution.md` | which of the three deliberate differences each separating metric is attributed to |

[CONSTITUTION.md](CONSTITUTION.md) is binding, not aspirational — read it before changing
anything. [docs/api-notes.md](docs/api-notes.md) records what the pinned libraries actually
do, as opposed to what their documentation claims; several entries fail silently.

## Maintaining this repo

Everything below is for maintainers. A viewer never needs any of it — `pytest` stays the
only command required to see the result.

```
uv run python -m evals.cli --help     # record · calibrate · compare · report
uv run ruff check . && uv run mypy .  # lint and types
```

A local `record` run only writes cache entries — it is billed, and it is the CLI's one
command that reads a provider credential, but it does not open a pull request itself. In
CI (`.github/workflows/live.yml`), `record` runs and is then followed by `gh pr create`, so
the evidence arrives as a reviewable diff. Outside the CLI, two other scripts also write
evidence under their own credential reads — `app/smoke_check.py` and
`evals/ops/regression_demo.py` — both run by hand, never by CI. Across all of them the
single-writer guarantee holds repo-wide (`tests/test_one_door.py` enforces it): every write
goes through one sanctioned path, `record` just isn't the only caller of it.

Live scoring needs two independent opt-ins together — the `live` marker *and* `EVAL_LIVE=1`.
Either alone skips, on purpose: one switch has too many plausible accidental causes, and the
failure mode is spending money you did not mean to spend.

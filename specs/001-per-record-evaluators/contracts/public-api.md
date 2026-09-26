# Contract: Public Python API, v1.1.0 (additive)

**Audience**: callers of the `trustnoagent` package, including the downstream platform in `docs/research/brief.md`. Types: [../data-model.md](../data-model.md).

## Stability

- Every name below is public from v1.1.0 and follows semver from then on: minor releases add, and only a major release removes or renames.
- Evaluator ids, once released, never change meaning (FR-009).
- The v1.0.0 surface is frozen and must stay byte-identical in behaviour: `EvalSuite`, `RunSummary`, `run_gate`, `Mode`, and the CLI commands `record`, `calibrate`, `compare`, `report` and `gate`.

## Exports added to `trustnoagent`

```python
from trustnoagent import (
    evaluate, list_evaluators,               # the Article II.c facade (trustnoagent/evaluators.py)
    EvalRecord, EvalResult, EvaluatorInfo,   # evals/contract.py
    JudgeConfig,                             # evals/judge_config.py
    RubricJudge,                             # evals/rubric.py
)
```

### `evaluate`

```python
def evaluate(
    evaluator: str | RubricJudge,
    record: EvalRecord,
    judge: JudgeConfig | None = None,
    cache_dir: Path | None = None,
) -> EvalResult
```

- **Synchronous.** It never returns a coroutine and never needs a running event loop from the caller.
- **Evaluator.** Either a built-in id from `list_evaluators()`, or a `RubricJudge` definition.
- **`judge=None`** means `JudgeConfig.from_env()`, which is offline. Live requires an explicit `JudgeConfig.from_env(mode="live")`, or a hand-built config with `mode="live"`.
- **`cache_dir=None`** means the committed `evals/.judge_cache/` when running inside a repo checkout, and an `error` result otherwise. The directory must follow the layout in [cache-entry.md](cache-entry.md).
- **Never raises for evaluation-time failures** (FR-004). Status semantics are in the data model.
- **May raise `TypeError`** when `record` is not an `EvalRecord`, since that is a caller programming error.

### `list_evaluators`

```python
def list_evaluators(*rubrics: RubricJudge) -> list[EvaluatorInfo]
```

- Returns the built-ins, sorted by id, followed by the given rubrics in the order passed.
- Needs no credentials, no model env vars and no network (FR-012).

### `JudgeConfig.from_env`

```python
@classmethod
def from_env(cls, mode: Mode = "offline") -> JudgeConfig
```

- Reads `JUDGE_MODEL` and `GENERATOR_MODEL` through the existing required accessors, and raises their existing `RuntimeError` if either is unset.
- Reads `NVIDIA_API_KEY` only when `mode == "live"`, and never raises for its absence.
- `base_url` is always the hardcoded NIM constant.

### `RubricJudge`

```python
RubricJudge(
    name: str,                           # ^[a-z0-9_]+$  -> id "tna.judge.<name>"
    instructions: str,
    requires: frozenset[str],            # subset of {"input","output","expected","contexts"}
    labels: tuple[str, ...] | None = None,
    score_range: tuple[float, float] | None = None,   # exactly one of labels/score_range
)
```

Construction raises `ValueError` on an invalid definition. The judge's reply must be JSON: `{"label": ..., "reason": ...}` or `{"score": ..., "reason": ...}`. Anything else yields `invalid_output`, with the text kept in `raw["responses"]`.

## Built-in evaluator catalogue (v1.1.0)

| id | version | requires | output_type |
|---|---|---|---|
| `tna.deepeval.refusal_correctness` | `1.1.0+deepeval@4.2.0` | `input`, `output`, `expected` | `score` (0–1) |
| `tna.ragas.response_relevancy` | `1.1.0+ragas@0.4.3` | `input`, `output` | `score` (0–1) |

## Example

```python
from trustnoagent import EvalRecord, JudgeConfig, evaluate

record = EvalRecord(input="How many PTO days?", output="Twenty days per year.")
result = evaluate("tna.ragas.response_relevancy", record)       # offline, committed evidence
live = evaluate("tna.ragas.response_relevancy", record,
                JudgeConfig.from_env(mode="live"), cache_dir=Path(".eval-cache"))
```

## Explicitly not part of this contract

- Async variants.
- Plugin or entry-point discovery.
- Any env var for the base URL or the cache directory.
- Batch APIs, storage, statistics or comparisons across results.
- Sampling parameters on any evaluator.

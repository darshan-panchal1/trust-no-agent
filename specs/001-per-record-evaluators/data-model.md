# Data Model: Per-Record Evaluator Contract

**Feature**: [spec.md](spec.md) · **Research**: [research.md](research.md)

All public types are frozen dataclasses or plain literals, defined in framework-free modules (Article II.c). No Ragas or DeepEval type appears in any field.

## Literals (`evals/contract.py`)

| Name | Values |
|---|---|
| `Status` | `"ok"`, `"error"`, `"skipped"`, `"invalid_output"` |
| `OutputType` | `"score"`, `"label"`, `"bool"` |
| `Provenance` | `"recorded"`, `"not_recorded"` |
| `RecordField` | `"input"`, `"output"`, `"expected"`, `"contexts"` |
| `Mode` | `"offline"`, `"live"`. This reuses the existing `trustnoagent.Mode` values; it is not a second definition that could drift. |

## EvalRecord (`evals/contract.py`)

One caller-supplied unit to score.

| Field | Type | Default | Notes |
|---|---|---|---|
| `input` | `str \| None` | `None` | The question or user turn. |
| `output` | `str \| None` | `None` | The candidate answer. |
| `expected` | `str \| None` | `None` | The reference answer. |
| `contexts` | `tuple[str, ...] \| None` | `None` | The retrieved passages, in order. A tuple so the record stays hashable and frozen. |
| `metadata` | `Mapping[str, str]` | empty | Carried through to the result's `raw`, and never sent to a judge. |

**Validation.**
- A field is **present** when it is not `None`. An empty string or an empty tuple counts as present (spec Edge Cases).
- There is no golden-case schema coupling: no `category`, no `expected_tools` (FR-002).

## JudgeConfig (`evals/judge_config.py`)

| Field | Type | Source in `from_env(mode)` |
|---|---|---|
| `judge_model` | `str` | `evals.models.judge_model()`: required, never defaulted. |
| `generator_model` | `str` | `evals.models.generator_model()`: required, never defaulted. |
| `mode` | `Mode` | The argument; defaults to `"offline"`. |
| `api_key` | `str \| None`, declared `repr=False` | `os.environ.get("NVIDIA_API_KEY")` when `mode == "live"`, else `None`. |
| `base_url` | `str` | Always `evals.models.NIM_BASE_URL`. This is not an env lookup (FR-025). |

**Rules.**
- `from_env()` raises the accessors' existing `RuntimeError` when a model variable is unset (FR-024).
- It never raises for a missing key. The evaluator reports `error` on use (FR-018).
- It is frozen and compared by value. `api_key` never appears in `repr`.

## Evaluator protocol and EvaluatorInfo (`evals/contract.py`)

```text
Evaluator (typing.Protocol, structural; nothing inherits it)
  id: str                    # "tna.ragas.response_relevancy"
  version: str               # "1.1.0+ragas@0.4.3"
  requires: frozenset[RecordField]
  output_type: OutputType
  evaluate(record: EvalRecord, judge: JudgeConfig) -> EvalResult   # synchronous
```

`EvaluatorInfo` is a frozen dataclass with `id`, `version`, `requires` and `output_type`. It is what `list_evaluators()` returns. Evaluator objects are never handed to callers.

**Registered in v1.1.0:**

| id | requires | output_type | template_version | call_kind(s) |
|---|---|---|---|---|
| `tna.ragas.faithfulness` | `{input, output, contexts}` | `score` | `ragas@0.4.3/1` | `ragas:faithfulness` |
| `tna.ragas.context_recall` | `{input, contexts, expected}` | `score` | `ragas@0.4.3/1` | `ragas:context_recall` |
| `tna.ragas.context_precision` | `{input, contexts, expected}` | `score` | `ragas@0.4.3/1` | `ragas:context_precision` |
| `tna.ragas.response_relevancy` | `{input, output}` | `score` | `ragas@0.4.3/1` | `ragas:response_relevancy`, plus `ragas:embeddings` (not fingerprinted) |
| `tna.deepeval.refusal_correctness` | `{input, output, expected}` | `score` | `refusal-steps/1` | `deepeval:refusalcorrectness` |
| `tna.judge.<name>` (per rubric) | as declared | `label` or `score` | content hash | `deepeval:judge.<name>` |

`requires` mirrors each metric's own `_required_columns` in ragas 0.4.3 (`user_input`→`input`, `response`→`output`, `retrieved_contexts`→`contexts`, `reference`→`expected`), verified 2026-09-26. The `call_kind` values for the built-ins are **the same strings the v1 path uses**. That is why identical inputs hit committed evidence (spec Assumptions; SC-002).

## RubricJudge (`evals/rubric.py`)

| Field | Type | Validation |
|---|---|---|
| `name` | `str` | Must match `^[a-z0-9_]+$`, otherwise `ValueError` at construction (a caller programming error; FR-004 allows raising). |
| `instructions` | `str` | Non-empty. |
| `requires` | `frozenset[RecordField]` | Non-empty. These are the fields the instructions render. |
| `labels` | `tuple[str, ...] \| None` | Exactly one of `labels` or `score_range` must be set. `labels` must be non-empty with no duplicates. |
| `score_range` | `tuple[float, float] \| None` | Requires `min < max`. |

**Derived values.**
- `id` = `tna.judge.<name>`.
- `output_type` = `label` when `labels` is set, otherwise `score`.
- `template_version` = `sha256(canonical_json(instructions, requires, labels, score_range))[:16]`. Any content change moves it (FR-022).

**Verdict schema.**
- With labels: `{"label": <one of labels>, "reason": str}`.
- With a range: `{"score": number with min ≤ score ≤ max, "reason": str}`.

The schema's canonical JSON Schema is the fingerprint's `schema` component.

## EvalResult (`evals/contract.py`)

| Field | Type | Rule |
|---|---|---|
| `evaluator_id` | `str` | Echoes the requested id. For an unknown id, echoes it verbatim. |
| `evaluator_version` | `str` | Empty when the id is unknown. |
| `status` | `Status` | See the transitions below. |
| `score` | `float \| None` | Set only when `status == "ok"` and the output type is `score`. Never NaN (FR-014). |
| `label` | `str \| None` | Set only when `status == "ok"` and the output type is `label`. |
| `explanation` | `str \| None` | The GEval reason, or the rubric `reason`. Otherwise `None`. |
| `judge_model` | `str \| None` | `JudgeConfig.judge_model` when a judge was consulted. |
| `judge_fingerprint` | `str \| None` | The result fingerprint (below). `None` only when no configuration was reached: an unknown id, or a missing model variable. |
| `fingerprint_provenance` | `Provenance \| None` | `recorded` if every judge entry served carried a stored fingerprint, `not_recorded` if any did not. `None` when no entry was served. |
| `latency_ms` | `int`, declared `compare=False` | Wall time of this call, set by the facade. It is excluded from equality (SC-005). |
| `tokens_in` / `tokens_out` | `int \| None` | Summed over distinct judge-kind keys served. `None` if any contributing entry is 0/0 or no entry was served (R6). |
| `error` | `str \| None` | Set when `status` is `error`, `skipped` or `invalid_output`. |
| `raw` | `Mapping[str, object]` | Audit payload: `cache_keys` served (sorted), `responses` (the judge text, where one exists), and the record `metadata`. It is deterministic, so it takes part in equality. |

## Status transitions

Rows are evaluated top to bottom, and the first match wins. Each row is one terminal state; there are no retries beyond `json_completion`'s existing single retry.

1. The id is unknown, or is a bare `tna.judge.*` string → **error**
2. The judge configuration can't be built (model variable unset) → **error**
3. `cache_dir` is absent outside a repo checkout → **error**
4. A required field is absent → **skipped**
5. Live mode and `api_key is None` → **error**
6. Judging (Ragas, GEval or the rubric judge) ends in one of:
   - `CacheMiss`, `FingerprintMismatch`, `ImportError`, or any other exception → **error**
   - unparseable, wrong-shaped, out-of-set or out-of-range output, or NaN → **invalid_output**
   - a valid score or label → **ok**

## Fingerprints (`evals/fingerprint.py`)

```text
config_fingerprint = sha256(canonical_json({
    "judge_model": JudgeConfig.judge_model,
    "template": f"{template_id}@{template_version}",   # template_id == evaluator id
    "decoding": <params actually sent>,                # see below
    "schema": <canonical output schema>,
}))
result_fingerprint = sha256(config_fingerprint + ":" + rendered_prompt_hash)
```

- **`decoding`.**
  - Ragas: `llm.model_args` as built, after Article III's pops; today this is `{"max_tokens": 32000}`.
  - GEval and rubric: `{"response_format": json_completion.RESPONSE_FORMAT}`.
  - No sampling parameter ever appears, because Article III bans them.
- **`schema`.**
  - Rubric: its verdict model's JSON Schema.
  - Ragas and GEval, whose schemas are internal to the pinned library: `"<lib>@<version>:<MetricClass>"`.
- **`rendered_prompt_hash`.**
  - Rubric: the hash of the exact prompt sent.
  - Ragas and GEval, which render internally: the hash of the canonical JSON of the record fields in `requires`.
- **Stored in each new cache entry:** `config_fingerprint` only (R2).

## CacheEntry extension (`evals/cache/store.py`)

These are the v1 fields, unchanged, plus one optional field:

| Field | Type | Serialised |
|---|---|---|
| `call_kind`, `response`, `input_tokens`, `output_tokens`, `usd` | unchanged | unchanged |
| `fingerprint` | `str \| None = None` | Omitted when `None` (`exclude_if`), so v1 bytes are identical. |

On-disk format: [contracts/cache-entry.md](contracts/cache-entry.md).

## Judging session (internal; `evals/cache/session.py`)

This state exists only for the duration of one new-path evaluation. It is not public, and nested sessions raise.

| State | Purpose |
|---|---|
| `fingerprint` | The expected configuration fingerprint, compared on every read and stamped on every write. |
| `judge_call_kind` | The only `call_kind` that is fingerprinted and paired with usage. |
| `pending_usage` | A FIFO of `(prompt_tokens, completion_tokens)` pushed by the instructor hook (R5). |
| `served` | `{key: CacheEntry}` for judge-kind entries read or written. It is the source of tokens, provenance and `raw.cache_keys`. |

`evals/cache/location.py` holds the separate directory override (R1), set by the facade.

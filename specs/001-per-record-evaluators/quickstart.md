# Quickstart: Validating the Per-Record Evaluator Contract

**Feature**: [spec.md](spec.md) · **API**: [contracts/public-api.md](contracts/public-api.md) · **Types**: [data-model.md](data-model.md)

Every step except §7 runs offline, with no API key, and must print `$0.00`.

## Prerequisites

```bash
uv sync --frozen          # exact pins; no new dependency is introduced by this feature
```

`JUDGE_MODEL` and `GENERATOR_MODEL` come from `pyproject.toml`'s pytest `env` block. Outside pytest, export the same committed values:

```bash
export JUDGE_MODEL=nvidia/nemotron-3-super-120b-a12b GENERATOR_MODEL=nvidia/nemotron-3-super-120b-a12b
export DEEPEVAL_TELEMETRY_OPT_OUT=YES RAGAS_DO_NOT_TRACK=true DEEPEVAL_DISABLE_DOTENV=1
```

## 1. The whole suite is still green (Article 0)

```bash
uv run pytest && uv run ruff check . && uv run mypy .
```

**Expected:**
- green;
- the cost table ends `$0.00` with a 100% cache hit rate;
- no module is over 60 lines;
- `tests/test_article_ii_facade.py` and `tests/test_v1_compat.py` both pass.

## 2. A committed answer scores offline, and matches the v1 path (US1, SC-002)

This covers built-in records, whose evidence is already committed: a golden case plus its `v2_fixed` answer.

```bash
uv run pytest tests/test_per_record_ragas_v1.py tests/test_per_record_ragas_v1_negative.py \
  tests/test_per_record_refusal_v1.py tests/test_per_record_fingerprint_legacy.py
```

**Expected** for all five built-in ids:
- status `ok`, with a score equal to the v1 per-case score for the same case;
- `fingerprint_provenance == "not_recorded"`, because it is a v1.0.0-era entry;
- `tokens_in is None` for Ragas, since the v1 entries record 0/0.
- the worst `v1_naive` answer misses the calibrated bar on the two gated Ragas metrics (the negative tests).

## 3. Every failure class becomes a status, never an exception (US3, SC-004)

Selects the `test_per_record_statuses_*` files (40 tests as of v1.1.0).

```bash
uv run pytest tests -k "per_record and statuses" -q
```

**Expected:** one record for each row of the research table's failure mapping (R10) produces the listed status. The score is `None` on every non-`ok` result, and no exception escapes.

## 4. Rubric judge: pass, fail, and invalid output (US4, SC-006, Article XI)

Selects every test file with `rubric` in its name (39 tests as of v1.1.0). Offline, the `fail` verdict is seeded evidence: it proves the path carries a failing label unchanged, not that a real judge reaches it (see §7).

```bash
uv run pytest tests -k "rubric" -q
```

**Expected:**
- A label rubric returns `ok` with `label="pass"` on a known-good record, and `label="fail"` on a known-bad one. This is the negative test.
- A score of 7 against the range 1–5 returns `invalid_output`, with the raw text kept.
- Two rubrics with the same name but different instructions produce different fingerprints.

## 5. Live-mode mechanics without the network (US6, US7, SC-005, SC-007)

```bash
uv run pytest tests/test_per_record_fingerprint.py tests/test_per_record_fingerprint_tamper.py \
  tests/test_per_record_ragas_tokens.py tests/test_per_record_ragas_tokens_edges.py \
  tests/test_per_record_rubric_live.py
```

These tests use an `httpx.MockTransport`-backed NIM client under `socket_disabled`, writing to a `tmp_path` cache. **Expected:**
- First call: status `ok`, real token counts (not 0/0), and an entry written with `fingerprint`.
- Second call: no HTTP request, and a result equal to the first in every field except `latency_ms`.
- Editing the stored `fingerprint` makes the next call return `error` naming both values, on every built-in and the rubric path.
- A retried judge attempt's tokens are billed to the entry it produced (Phase 9 correction to R5).

## 6. v1.0.0 behaviour is byte-identical (SC-003)

- **In the suite:** step 1 already covers it, through `tests/test_v1_compat.py`. That module checks cache re-serialisation of all 1,120 entries, the `make_key` golden hash, the `RunSummary` schema snapshot, and that the offline summary is fully cached.
- **For the CLI:** the `compat` workflow runs on the pull request. It compares `v1.0.0` against HEAD for `record --dry-run`, `report`, `compare` and `gate`, including stdout and exit codes, and runs `calibrate` followed by `git diff --exit-code evals/thresholds.yaml`. **Expected:** zero diff.
- **Locally**, the same comparison is the sequence of steps inside `.github/workflows/compat.yml`, run by hand in two `git worktree`s.

## 7. Live, by hand, once (never CI, never pytest)

```bash
uv sync --frozen --group calibration                 # only for the response_relevancy embeddings
NVIDIA_API_KEY=... uv run python -c "from trustnoagent.live_check import main; main()"
```

**Expected:**
- Each built-in and one sample rubric score a fresh record into a temporary `cache_dir`.
- Each prints status, score or label, tokens and fingerprint.

**Recorded run, 2026-09-26** (`nvidia/nemotron-3-super-120b-a12b`, 12m47s, 16 uncached calls; re-run: 0 uncached calls, identical results). One faithful and one known-bad (wrong, ungrounded, rude) answer:

| evaluator | good | bad |
|---|---|---|
| faithfulness | 0.5 | 0.0 |
| response_relevancy | 0.83 | 0.58 |
| context_precision / context_recall | 0.50 / 1.0 | 0.50 / 1.0 (they never read the answer) |
| refusal_correctness | 1.0 | 0.9 (it asks "answer or refuse?", and both answered) |
| rubric `polite_and_grounded` | `pass` | `invalid_output`: the judge replied `{}` |

The `{}` is `json_object` mode's documented weakness (valid JSON, no fields). The path reported it with the reply kept, not as a verdict. `nvext.guided_json` is the known fix (research R18).
- A second run makes zero HTTP calls.
- `evals/.judge_cache/` is untouched, which `git status` confirms.

# Tasks: Per-Record Evaluator Contract

**Input**: Design documents from `specs/001-per-record-evaluators/`: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Requested, TDD. In every phase, write the phase's tests first and watch them fail (red) before implementing. Regression guards that protect existing behaviour are the one exception: they are written first and are **expected to pass immediately**. Each is marked "guard".

**Gate**: every phase ends with **GATE**:

```bash
uv run pytest && uv run ruff check . && uv run mypy .
```

Expected: green, the cost table ends `$0.00` with a 100% cache hit rate, and mypy is strict and clean. The Phase 1 baseline is 131 passed, 2 skipped, 3 xfailed.

## Rules that apply to every task (from CONSTITUTION.md and the existing enforcement tests)

1. **The 60-line cap applies to every `.py` file, tests included** (`tests/test_module_size.py`). When a file would pass 60 lines, split it: `_a`/`_b` suffixes for tests, a sibling module for source.
2. **No file may import both `evals.component` and `evals.behavior`** (`tests/test_article_ii_facade.py`). Only `trustnoagent/evaluators.py` may. Tests reach both layers **through the facade**, or through `evals.ops.*`, never by importing both layer packages directly.
3. **`evals/component/**` never imports `deepeval`, and `evals/behavior/**` never imports `ragas`** (`tests/test_constitution.py`).
4. **No new file may call `read_or_call`.** `tests/test_one_door.py` pins the caller set with `==`. Tests seed evidence by writing entry files directly, as `tests/test_judge.py` does. Live writes happen through the existing sanctioned writers (`CachedJudge`, `RagasCacheBackend`, `app/generate.py`).
5. **DeepEval judge models are constructed only in `evals/judge/`** (Article VI.a). The rubric judge therefore gets a factory in that package (T043).
6. **No `temperature`/`top_p`/`top_k` anywhere** (Article III). **No `async def` in new code** (Article X). **No `if __name__ == "__main__"`** outside `app/` and `evals/cli.py` (Article I).
7. **Tests that use the `isolated_cache` fixture must pass `cache_dir=store.CACHE_DIR` explicitly.** The tmp directory is not a repo checkout, so the default would return `error`, which is correct behaviour.
8. **Offline tests use `@pytest.mark.usefixtures("socket_disabled")`.** Live-mechanics tests use an `httpx.MockTransport`-backed client, never a socket.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task).
- **[Story]**: US1–US7 from [spec.md](spec.md).

---

## Phase 1: Setup

**Purpose**: confirm the baseline and set the release version, so evaluator version strings are right from the first test.

- [ ] T001 Confirm the branch is `001-per-record-evaluators` and run GATE against `pyproject.toml`'s configuration. Record the baseline counts (expected: 131 passed, 2 skipped, 3 xfailed, `$0.00`) in the PR description draft.
- [ ] T002 Bump the version from `1.0.0` to `1.1.0` in `pyproject.toml` (`[project] version`) and `trustnoagent/__init__.py` (`__version__`). Then run `uv lock --offline` and confirm `git diff uv.lock` shows only the `trust-no-agent` version line (around line 2203). Run GATE.

**Checkpoint**: GATE green. The version is 1.1.0 and no behaviour has changed.

---

## Phase 2: Foundational (blocks every story)

**Purpose**: the framework-free contract types, the judge configuration, fingerprints, and the store-level cache-directory override and judging session (research R1, R2, R4, R6). Plus the v1 regression guards, which land **before** `store.py` is touched.

### Tests first

- [ ] T003 [P] **Guard.** Write `tests/test_v1_compat.py`, which must pass immediately:
  - (a) Every file in `evals/.judge_cache/` round-trips byte-identically: `CacheEntry.model_validate_json(t).model_dump_json() == t`. Assert the file count is ≥1120 and equals the number checked.
  - (b) `make_key("ragas:faithfulness", "m", "p")` equals a golden hex string. Compute it once, now, and paste it in as a literal.
- [ ] T004 [P] **Guard.** Write `tests/test_v1_compat_summary.py`, which must pass immediately:
  - (a) `RunSummary.model_json_schema()` equals `tests/snapshots/run_summary_schema.json`. Generate that snapshot now, from the unchanged code, with `json.dumps(..., indent=2, sort_keys=True)`.
  - (b) Offline `evals.ops.summary.build_summary()`, bracketed by `cost.reset()`, raises no `CacheMiss`, and every `cost.rows()` row has `cached == calls`.
  - Use `socket_disabled`. Unlike existing fixtures, this **fails** on a miss rather than skipping.
- [ ] T005 [P] Write `tests/test_contract_types.py` for `evals/contract.py`:
  - `EvalRecord` is frozen, its fields default to `None`, and `metadata` defaults to empty;
  - an empty string or empty tuple counts as present;
  - `EvalResult` equality ignores `latency_ms` (`field(compare=False)`);
  - `get_args(Status) == ("ok","error","skipped","invalid_output")`, and likewise for `OutputType`, `Provenance` and `RecordField`;
  - `trustnoagent.Mode is evals.contract.Mode`.
- [ ] T006 [P] Write `tests/test_judge_config.py` for `evals/judge_config.py`:
  - `from_env()` returns the pytest-env models, `mode="offline"` and `api_key=None`;
  - with `JUDGE_MODEL` deleted (`monkeypatch.delenv`), it raises the existing `RuntimeError` whose message names `JUDGE_MODEL`, and the same for `GENERATOR_MODEL`;
  - `from_env(mode="live")` with `NVIDIA_API_KEY` set via monkeypatch returns it, and with it unset returns `None` without raising;
  - with `monkeypatch.setenv("NIM_BASE_URL", "http://evil")`, `base_url == evals.models.NIM_BASE_URL`;
  - `"nvapi" not in repr(JudgeConfig(..., api_key="nvapi-x"))`.
- [ ] T007 [P] Write `tests/test_fingerprint.py` for `evals/fingerprint.py`:
  - `canonical_json` is independent of dict key order;
  - `config_fingerprint(judge_model, template, decoding, schema)` is deterministic and changes when any one argument changes;
  - `result_fingerprint(cfg, prompt_hash) == sha256(f"{cfg}:{prompt_hash}")`;
  - a `decoding` dict containing `temperature`, `top_p` or `top_k` raises `ValueError` (Article III).
- [ ] T008 [P] Write `tests/test_cache_location.py` for `evals/cache/location.py` and the store hook:
  - `default_cache_dir(store.CACHE_DIR)` returns `CACHE_DIR` in this checkout;
  - `default_cache_dir(tmp_path / "evals" / ".judge_cache")` returns `None`;
  - `with location.override(tmp_path):` makes `store.read_or_raise(key)` read a file written into `tmp_path`, and a miss names a path under `tmp_path`;
  - the override is restored after the block, including when the block raises.
- [ ] T009 [P] Write `tests/test_cache_session.py` for `evals/cache/session.py`. Use `isolated_cache` and exercise writes **only** through `RagasCacheBackend(..., mode="live").set/get` (rule 4).
  - With no session, a written entry's JSON has no `"fingerprint"` key and keeps 0/0 tokens.
  - Inside `session.begin(fingerprint="F", judge_call_kind="ragas:faithfulness")`:
    - a write to `ragas:faithfulness` carries `"fingerprint":"F"`;
    - a write to `ragas:embeddings` does not;
    - pending usages pushed with `push_usage` are paired FIFO with judge-kind writes only;
    - a read of an entry stored with `"fingerprint":"G"` raises `FingerprintMismatch` naming `F` and `G`;
    - a read of an entry with no fingerprint is recorded in `served`.
  - Nested `begin` raises `RuntimeError`.
  - The state is cleared after the block, even on an exception.

### Implementation

- [ ] T010 [P] Create `evals/contract.py`:
  - literals `Status`, `OutputType`, `Provenance`, `RecordField` and `Mode = Literal["offline","live"]`;
  - frozen dataclasses `EvalRecord`, `EvalResult` (per data-model.md; `latency_ms` with `compare=False`; `raw: Mapping[str, object]`) and `EvaluatorInfo`;
  - the `Evaluator` `typing.Protocol` (sync `evaluate(record, judge) -> EvalResult`), with `JudgeConfig` referenced under `TYPE_CHECKING`.
  - It imports stdlib only.
  - Then change `trustnoagent/suite.py` line 23 to `from evals.contract import Mode` (same object, no behaviour change; this avoids a circular import from the adapters).
- [ ] T011 [P] Create `evals/judge_config.py`:
  - a frozen `JudgeConfig(judge_model, generator_model, mode="offline", api_key=field(default=None, repr=False), base_url=NIM_BASE_URL)`;
  - `from_env(mode="offline")`, which calls `evals.models.judge_model()` and `generator_model()`, and reads `os.environ.get("NVIDIA_API_KEY")` only when `mode == "live"`.
- [ ] T012 [P] Create `evals/fingerprint.py` with:
  - `canonical_json(obj) -> str` (`sort_keys`, `separators=(",",":")`);
  - `config_fingerprint(judge_model, template, decoding, schema) -> str`, which rejects sampling keys;
  - `result_fingerprint(config_fp, prompt_hash) -> str`;
  - `record_hash(record, fields) -> str`, meaning `hash_prompt(canonical_json(...))` of the named fields, with contexts as a list.
- [ ] T013 [P] Create `evals/cache/location.py`:
  - a module-level `_override: Path | None`;
  - `current() -> Path | None`;
  - an `override(path)` context manager that restores in `finally`;
  - `default_cache_dir(committed: Path) -> Path | None`, which returns `committed` only when `committed.parents[1]` contains both `.git` (file or directory) and `pyproject.toml`.
  - It does not import `store`.
- [ ] T014 [P] Create `evals/cache/session.py`:
  - `FingerprintMismatch(RuntimeError)`, carrying `key`, `stored`, `expected` and the stored `response`;
  - a dataclass `_Session(fingerprint, judge_call_kind, pending_usage: deque[tuple[int,int]], served: dict[str, CacheEntry])`;
  - `begin(fingerprint, judge_call_kind)` as a context manager: it raises if a session is already active, and clears in `finally`;
  - `current()`;
  - `push_usage(response)`, an instructor `completion:response` handler that appends `(usage.prompt_tokens, usage.completion_tokens)`;
  - `observe(key, entry) -> entry`, which raises on a stored-fingerprint mismatch for judge-kind entries and records judge-kind entries in `served`;
  - `stamp(entry) -> entry`, which for the judge kind returns `entry.model_copy(update=...)` with the fingerprint and the next pending usage, if any.
  - Every function is a no-op passthrough when no session is active. Import `CacheEntry` only under `TYPE_CHECKING`, to avoid a cycle.
- [ ] T015 Change `evals/cache/store.py`, keeping it at 60 lines or fewer:
  - add `fingerprint: str | None = Field(default=None, exclude_if=lambda v: v is None)` to `CacheEntry`;
  - add `from evals.cache import location, session`;
  - in both functions, set `path = (location.current() or CACHE_DIR) / f"{key}.json"`;
  - on a hit, `return _record(session.observe(key, CacheEntry.model_validate_json(...)), cached=True)`;
  - in `read_or_call`, set `entry = session.stamp(call_fn())`, call `path.parent.mkdir(...)` instead of `CACHE_DIR.mkdir(...)`, and `return _record(session.observe(key, entry), cached=False)`.
  - `read_or_raise`'s signature stays `(key)`.
  - T003, T008 and T009 must now be green.
- [ ] T016 Create `evals/outcomes.py`, which imports no framework. Split into `evals/outcomes_tokens.py` if it nears 60 lines, and add that name to `CONTRACT_MODULES` in `tests/test_article_ii_facade.py`. It provides these builders:
  - `skipped(info, missing)` and `error(info, message, judge=None, fingerprint=None)`;
  - `invalid(info, message, raw_text, judge, fingerprint)`;
  - `ok(info, *, score=None, label=None, explanation=None, judge, fingerprint, served)`:
    - it computes `tokens_in`/`tokens_out` as sums over the `served` values, or `None` if any served entry is 0/0 or nothing was served (R6);
    - it sets `fingerprint_provenance` to `recorded` if every served entry has a fingerprint, else `not_recorded`, or `None` when nothing was served;
    - it sets `raw` to `{"cache_keys": sorted(served), "responses": [...]}`;
    - it turns a NaN score into `invalid`.
  - `latency_ms` defaults to 0; the facade sets it.
- [ ] T017 Create `tests/per_record_support.py` (not collected, no `test_` prefix, never imports both layers):
  - `golden_record(variant, index) -> tuple[GoldenCase, EvalRecord]`, built from `load_golden()` and `app.v1_naive`/`app.v2_fixed` `answer(q, mode="offline")`, with `contexts=tuple(c.text for c in result.retrieved_contexts)` and `expected=case.ground_truth`;
  - `mock_nim(handler) -> Callable[..., openai.OpenAI]`, a factory producing a real `openai.OpenAI` with `http_client=httpx.Client(transport=httpx.MockTransport(handler))`, which keeps a call counter.
- [ ] T018 Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`). T003–T009 are green; T003 and T004 were never red.

**Checkpoint**: contract types, configuration, fingerprints and the store hooks exist. With no session and no override active, the store is byte-for-byte v1.0.0 (T003 and T009 prove it).

---

## Phase 3: User Story 1: score one record with one named evaluator (P1) 🎯 MVP

**Goal**: `evaluate(id, EvalRecord)` returns one `ok` result for all five built-ins, served offline from committed evidence, with scores identical to the v1 path.

**Independent test**: T019–T021 pass offline with `socket_disabled` and `$0.00`.

### Tests first

- [ ] T019 [P] [US1] Write `tests/test_per_record_ragas_v1.py`. Use a session-scoped fixture computing `evals.ops.ragas_means.ragas_results(cases, answers)` once.
  - For each of `faithfulness`, `context_recall`, `context_precision` and `response_relevancy`, and for golden indices 0 and 1 under both variants: `evaluate(f"tna.ragas.{name}", record)` has status `ok`, `score == pytest.approx(v1_per_case, abs=1e-9)`, `fingerprint_provenance == "not_recorded"`, `tokens_in is None` (v1 Ragas entries are 0/0), and a non-empty `judge_fingerprint`.
  - **Negative (Article XI):** at least one `v1_naive` record scores below `threshold_for(name)` for `faithfulness` and for `context_recall`.
  - Split into `_a`/`_b` if it passes 60 lines.
- [ ] T020 [P] [US1] Write `tests/test_per_record_refusal_v1.py`: using `evals.ops.refusal_means.measured(...)`, every relevant golden case under both variants gives `evaluate("tna.deepeval.refusal_correctness", record)` status `ok`, the same score, a non-empty `explanation`, and real (non-`None`) tokens. **Negative:** at least one `v1_naive` case scores below 0.5.
- [ ] T021 [P] [US1] Write `tests/test_per_record_surface.py`:
  - `inspect.iscoroutinefunction(trustnoagent.evaluate) is False`;
  - `evaluate` scoring the same golden record twice returns equal results (SC-005), with every served call counted as cached in `cost.rows()`;
  - passing a non-`EvalRecord` raises `TypeError`;
  - an AST check that this test file imports nothing from `ragas`, `deepeval`, `openai` or `instructor` (FR-005).

### Implementation

- [ ] T022 [P] [US1] Add `record_to_sample(record: EvalRecord) -> SingleTurnSample` to `evals/adapters/ragas_adapter.py`. It maps `input→user_input`, `contexts→retrieved_contexts` (as a list), `expected→reference` and `output→response`, and must produce a sample equal to `to_single_turn_sample` for a golden-derived record. `to_single_turn_sample` is unchanged.
- [ ] T023 [P] [US1] Add `record_to_test_case(record) -> LLMTestCase` to `evals/adapters/deepeval_adapter.py`. It sets `input`, `actual_output`, `expected_output` and `retrieval_context`. That is enough: RefusalCorrectness renders only INPUT, ACTUAL_OUTPUT and EXPECTED_OUTPUT, so the GEval prompt is identical. `to_llm_test_case` is unchanged.
- [ ] T024 [P] [US1] Add `RESPONSE_FORMAT: Final = {"type": "json_object"}` to `evals/judge/json_completion.py` and use it in the existing `create(...)` call. Behaviour is unchanged.
- [ ] T025 [US1] In `evals/component/matrix.py`, extract `build_metric(name, mode) -> Metric`, with the exact constructor arguments used today. Make `build_metrics(mode)` return `[build_metric(n, mode) for n in METRIC_NAMES]`: same order, same objects. This is guarded by T003, T004 and the existing component tests.
- [ ] T026 [US1] Create `evals/component/record_eval.py`, which is ragas-only; put the table in `evals/component/record_metrics.py` if it nears 60 lines.
  - Export `LIB = f"ragas@{ragas.__version__}"`, `TEMPLATE_VERSION = f"{LIB}/1"`, and a `REQUIRES` table:
    - faithfulness: `{input, output, contexts}`
    - context_recall and context_precision: `{input, contexts, expected}`
    - response_relevancy: `{input, output}`
  - Export `evaluate_ragas(name, info, record, judge) -> EvalResult`:
    - return `outcomes.skipped` on the first missing required field;
    - `metric = build_metric(name, judge.mode)`;
    - `cfg = config_fingerprint(judge.judge_model, f"tna.ragas.{name}@{TEMPLATE_VERSION}", dict(metric.llm.model_args), f"{LIB}:{type(metric).__name__}")`;
    - `with session.begin(cfg, f"ragas:{name}"): score = metric.single_turn_score(record_to_sample(record))`;
    - `outcomes.ok(...)` with `result_fingerprint(cfg, record_hash(record, REQUIRES[name]))` and `session.current().served` captured before exit.
  - **If T019 shows cache misses**, the prompt shape differs from the v1 path. Switch the scoring call to `evaluate(EvaluationDataset(samples=[sample]), metrics=[metric], raise_exceptions=True, show_progress=False)`, the exact call shape `evals/ops/ragas_means.py` uses, and read `result[name][0]`.
- [ ] T027 [US1] Create `evals/behavior/record_eval.py`, which is deepeval-only.
  - Export `LIB = f"deepeval@{deepeval.__version__}"`, `TEMPLATE_VERSION = "refusal-steps/1"` and `REQUIRES = {input, output, expected}`.
  - `evaluate_refusal(info, record, judge)`:
    - `metric = build_refusal_correctness_metric(judge.mode)`;
    - `cfg` uses decoding `{"response_format": RESPONSE_FORMAT}` and schema `f"{LIB}:GEval"`;
    - inside `session.begin(cfg, "deepeval:refusalcorrectness")`, call `metric.measure(record_to_test_case(record))` directly (never `assert_test`);
    - return `outcomes.ok(score=metric.score, explanation=metric.reason, ...)`.
- [ ] T028 [US1] Create `trustnoagent/evaluators.py`, the Article II.c facade, which imports no framework.
  - `REGISTRY: dict[str, Callable[[EvaluatorInfo, EvalRecord, JudgeConfig], EvalResult]]` holds the four ragas ids (via `functools.partial(evaluate_ragas, name)`) and `tna.deepeval.refusal_correctness`, filled by direct import.
  - `INFOS: dict[str, EvaluatorInfo]` holds `version = f"{__version__}+{LIB}"` from each layer's `LIB`. Import `__version__` from a leaf, `trustnoagent/version.py`, created here to avoid a circular import from `trustnoagent/__init__.py`. `__init__` re-exports it, so `trustnoagent.__version__` is unchanged.
  - `evaluate(evaluator, record, judge=None, cache_dir=None)`:
    - raise `TypeError` if `record` is not an `EvalRecord`;
    - `judge = judge or JudgeConfig.from_env()`;
    - `directory = cache_dir or default_cache_dir(store.CACHE_DIR)`;
    - `with location.override(directory):` time the registry call and return `dataclasses.replace(result, latency_ms=...)`.
  - Unknown ids and failure mapping come in US2 and US3.
- [ ] T029 [US1] Export `evaluate`, `EvalRecord`, `EvalResult`, `EvaluatorInfo` and `JudgeConfig` from `trustnoagent/__init__.py`, keeping every v1.0.0 export.
- [ ] T030 [US1] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`). T019–T021 are green.

**Checkpoint (MVP)**: a caller scores any of the five metrics on their own record through one import, offline, reproducing v1 exactly.

---

## Phase 4: User Story 2: discover what evaluators exist (P1)

**Goal**: `list_evaluators()` gives id, version, required fields and output type with no environment and no network. Unknown ids come back as results.

**Independent test**: T031 passes with all three env vars deleted.

- [ ] T031 [P] [US2] Write `tests/test_per_record_listing.py`:
  - `list_evaluators()` returns exactly the five ids, sorted, each matching `^tna\.(ragas|deepeval)\.[a-z_]+$`;
  - each `version` equals `f"{trustnoagent.__version__}+ragas@{pin}"` (or `deepeval@{pin}`), where `pin` is parsed from `pyproject.toml` with `tomllib` (`ragas==0.4.3`, `deepeval==4.2.0`);
  - `requires` and `output_type` equal the table in `contracts/public-api.md`;
  - it passes with `JUDGE_MODEL`, `GENERATOR_MODEL` and `NVIDIA_API_KEY` deleted, under `socket_disabled`;
  - `evaluate("tna.ragas.nope", record)` has status `error`, with `evaluator_id` echoed, `evaluator_version == ""` and a message naming the id.
- [ ] T032 [US2] Add `list_evaluators(*rubrics) -> list[EvaluatorInfo]` to `trustnoagent/evaluators.py`. For now it returns the built-ins sorted by id; rubrics are appended in US4. Also add an unknown-id branch returning `outcomes.error(EvaluatorInfo(id, "", frozenset(), "score"), ...)` before any judge configuration is read. Export it from `trustnoagent/__init__.py`.
- [ ] T033 [US2] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`).

---

## Phase 5: User Story 3: failures are results, not exceptions (P1)

**Goal**: every failure class in research R10 maps to its status. No exception escapes, and no failed result carries a score.

**Independent test**: T034 and T035 pass, and every non-`ok` result in them has `score is None` and `label is None`.

- [ ] T034 [P] [US3] Write `tests/test_per_record_statuses_input.py`:
  - a record missing `contexts`, scored with faithfulness → `skipped` naming `contexts`, with no new `cost.rows()` entries;
  - `contexts=()`, which is present → not `skipped`;
  - `evaluate("tna.judge.x", r)` → `error` explaining that rubrics are passed as definitions;
  - `JUDGE_MODEL` deleted with `judge=None` → `error` naming `JUDGE_MODEL`;
  - `location.default_cache_dir` monkeypatched to return `None`, with `cache_dir=None` → `error` asking for a directory;
  - a novel record (not in the golden set) offline → `error` naming a cache key and the word `live`.
- [ ] T035 [P] [US3] Write `tests/test_per_record_statuses_judge.py`. Monkeypatch the scoring call inside each layer module:
  - `float("nan")` → `invalid_output`;
  - ragas `RagasOutputParserException` → `invalid_output`;
  - pydantic `ValidationError` → `invalid_output`;
  - GEval `ValueError("Evaluation LLM outputted an invalid JSON...")` → `invalid_output`, with raw text kept;
  - `ImportError` → `error` naming `uv sync --group calibration`;
  - `RuntimeError("boom")` → `error` containing `RuntimeError: boom`.
  - Assert that no exception propagates. This file imports only the facade and `evals.component.record_eval`; use a second file for the behaviour-side patches, per rule 2.
- [ ] T036 [US3] In `evals/component/record_eval.py`, catch `RagasOutputParserException` and pydantic `ValidationError` → `outcomes.invalid`, and catch `ImportError` → `outcomes.error` naming `uv sync --group calibration`. NaN is already handled by `outcomes.ok`.
- [ ] T037 [US3] In `evals/behavior/record_eval.py`, catch a `ValueError` whose message contains "invalid JSON" → `outcomes.invalid`.
- [ ] T038 [US3] In `trustnoagent/evaluators.py`, apply the data-model transition order:
  1. unknown id / bare `tna.judge.*` → error;
  2. `JudgeConfig.from_env()` raising `RuntimeError` → error;
  3. missing directory → error;
  4. (layer) skipped;
  5. `CacheMiss` → error with "new records need live mode" appended;
  6. `except Exception` → error `f"{type(e).__name__}: {e}"` as the FR-004 safety net.
- [ ] T039 [US3] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`).

---

## Phase 6: User Story 4: custom rubric judge through the same path (P2)

**Goal**: a `RubricJudge` definition scores through `evaluate()` with labels or a score range, and invalid judge output becomes `invalid_output` with the raw text kept.

**Independent test**: T040 and T041 pass. The known-bad record produces the failing label (Article XI).

- [ ] T040 [P] [US4] Write `tests/test_rubric_definition.py` for `evals/rubric.py`:
  - names outside `^[a-z0-9_]+$` raise `ValueError`;
  - both or neither of `labels`/`score_range` raise, and so do duplicate labels and `min >= max`;
  - `id == "tna.judge.<name>"`;
  - `output_type` is `label` or `score`;
  - `template_version` changes when instructions, `requires`, labels or range change;
  - `render_prompt` includes only the `requires` fields and the reply-format instruction;
  - `verdict_model(r).model_validate_json` accepts `{"label":"pass","reason":"x"}`, and rejects an unknown label, a score outside the range, and `{}`.
- [ ] T041 [P] [US4] Write `tests/test_per_record_rubric.py` (split `_a`/`_b` as needed), using `isolated_cache` and `cache_dir=store.CACHE_DIR`.
  - Seed entries by writing files at `make_key(f"deepeval:judge.{name}", judge_model(), hash_prompt(render_prompt(r, rec)))`.
  - A good record with a `"pass"` entry → `ok`, `label="pass"`, `score is None`.
  - **Negative:** a bad record with a `"fail"` entry → `ok`, `label="fail"`.
  - Range 1–5 with `{"score":7}` → `invalid_output`, with `raw["responses"]` holding the text.
  - `{"verdict":"x"}` → `invalid_output`.
  - Same name, different instructions → different `judge_fingerprint`, and the second is not served the first's entry.
  - `list_evaluators(r)` ends with `r`'s info.
  - **Live:** `mock_nim` returns non-JSON content twice → `invalid_output`, with `raw` = that content and no file written.
- [ ] T042 [P] [US4] Create `evals/rubric.py`, which is framework-free (pydantic and stdlib only):
  - a frozen `RubricJudge(name, instructions, requires, labels=None, score_range=None)`, validated in `__post_init__`;
  - properties `id`, `output_type` and `template_version` (`sha256(canonical_json(...))[:16]`);
  - `render_prompt(rubric, record) -> str`;
  - `verdict_model(rubric) -> type[BaseModel]`, via `pydantic.create_model`, with `Literal[labels]` or `Annotated[float, Field(ge=min, le=max)]` plus `reason: str`;
  - `verdict_schema(rubric) -> dict` for the fingerprint.
- [ ] T043 [P] [US4] Add `build_rubric_judge(name, mode) -> CachedJudge` to a new `evals/judge/rubric_judge.py`, returning `CachedJudge(f"deepeval:judge.{name}", mode=mode)`. Export it from `evals/judge/__init__.py` (Article VI.a's one door).
- [ ] T044 [US4] Create `evals/behavior/rubric_eval.py`, which is deepeval-side and imports only `evals.judge`, `evals.rubric` and the contract modules:
  - `evaluate_rubric(rubric, record, judge)` skips on a missing field;
  - `cfg = config_fingerprint(judge.judge_model, f"{rubric.id}@{rubric.template_version}", {"response_format": RESPONSE_FORMAT}, verdict_schema(rubric))`;
  - inside `session.begin(cfg, f"deepeval:judge.{rubric.name}")`: `text = build_rubric_judge(rubric.name, judge.mode).generate(prompt)`;
  - `json.JSONDecodeError` → `invalid` with `raw=exc.doc`;
  - `verdict_model(...).model_validate_json(text)` raising `ValidationError` → `invalid` with `raw=text`;
  - otherwise `ok(label=... or score=..., explanation=verdict.reason)`.
- [ ] T045 [US4] In `trustnoagent/evaluators.py`: `evaluate()` accepts `RubricJudge` and routes it to `evaluate_rubric`; `list_evaluators(*rubrics)` appends each rubric's `EvaluatorInfo`, with `version = f"{__version__}+{deepeval LIB}"`. Export `RubricJudge` from `trustnoagent/__init__.py`.
- [ ] T046 [US4] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`).

---

## Phase 7: User Story 5: one judge configuration object (P2)

**Goal**: a `JudgeConfig`, whether from `from_env()` or built by hand, governs the call: its model drives the cache key, and its key is used for live calls. Live use without a key is an `error`, never an exception. (`JudgeConfig` itself landed in Phase 2, T006 and T011, because every story depends on it.)

**Independent test**: T047 passes, and `NVIDIA_API_KEY` is absent from `os.environ` after every test in it.

- [ ] T047 [P] [US5] Write `tests/test_per_record_judge_config.py`:
  - `JudgeConfig(judge_model="other/model", ...)` scoring refusal against a tmp cache seeded only under `other/model` → `ok`, which proves the config, not the env, drives the key;
  - `JudgeConfig.from_env(mode="live")` with no key → `error` naming `NVIDIA_API_KEY`, with no client constructed (monkeypatch `openai.OpenAI` to raise if called);
  - `judge_env` restores `JUDGE_MODEL`, `GENERATOR_MODEL` and `NVIDIA_API_KEY` to their prior state (including absent) after normal exit and after an exception.
- [ ] T048 [US5] Add `judge_env(config: JudgeConfig)` to `trustnoagent/env.py`. It exports `JUDGE_MODEL` and `GENERATOR_MODEL`, plus `NVIDIA_API_KEY` when `config.api_key` is set, restoring prior values in `finally`, mirroring `model_env`, which stays unchanged.
- [ ] T049 [US5] In `trustnoagent/evaluators.py`: after resolving `judge`, if `judge.mode == "live"` and `judge.api_key is None`, return `error` naming `NVIDIA_API_KEY` (transition 5). Wrap the registry call in `judge_env(judge)`.
- [ ] T050 [US5] Run GATE. Confirm `tests/test_provider_credentials.py` stays green, since the key never outlives a call.

---

## Phase 8: User Story 6: every result carries a judging fingerprint (P2)

**Goal**: fingerprints are deterministic, stored beside the key on new-path writes, refused on mismatch, and marked `not_recorded` on v1 entries.

**Independent test**: T051 passes, and the committed cache is unchanged (`git status evals/.judge_cache` is clean).

- [ ] T051 [P] [US6] Write `tests/test_per_record_fingerprint.py`, using `isolated_cache`, `cache_dir=store.CACHE_DIR` and `mock_nim` injected by `monkeypatch.setattr(openai, "OpenAI", mock_nim(handler))` with a `JudgeConfig(mode="live", api_key="nvapi-test")`.
  - A live refusal call writes an entry whose JSON contains `"fingerprint"`.
  - An offline re-run returns an equal result with `fingerprint_provenance == "recorded"`.
  - Rewriting that file's `"fingerprint"` to `"0"*64`, then re-running, gives `error` whose message contains both the stored and the expected value, with the stored text in `raw["responses"]`.
  - Changing `judge_model` changes `judge_fingerprint`.
  - An old-path `CachedJudge(...).generate` live write under no session has no `"fingerprint"` key.
- [ ] T052 [US6] In `trustnoagent/evaluators.py`, map `FingerprintMismatch` to `error`: `f"stored fingerprint {stored} != current {expected} for {key}"`, with `raw={"responses":[exc.response], "cache_keys":[exc.key]}`. Place it before the generic `Exception` branch.
- [ ] T053 [US6] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`).

---

## Phase 9: User Story 7: real Ragas token counts on the new path (P3)

**Goal**: live Ragas evaluations report provider token usage, summed across judge calls. v1-era 0/0 entries report `None`. The old path still writes 0/0.

**Independent test**: T054 passes, with the mock transport's call count unchanged on the cached re-run.

- [ ] T054 [P] [US7] Write `tests/test_per_record_ragas_tokens.py`, using `isolated_cache`, `cache_dir=store.CACHE_DIR`, and faithfulness, which needs no embeddings. `mock_nim` returns an instructor TOOLS-mode reply chosen by the requested tool name: `StatementGeneratorOutput` → `{"statements":["s1"]}`; the NLI output → one verdict of 1. Each reply carries `usage` 123/45.
  - Live `evaluate("tna.ragas.faithfulness", rec, live_cfg)` → `ok`, `tokens_in == 246`, `tokens_out == 90`, and both written judge entries carry real tokens and a `fingerprint`.
  - Re-running makes no new HTTP calls and returns an equal result.
  - A `RagasCacheBackend("ragas:faithfulness", ..., mode="live").set(...)` outside `evaluate()` still writes 0/0.
  - Confirm the tool names against the pinned ragas before hard-coding them (`ragas/metrics/_faithfulness.py`).
- [ ] T055 [US7] In `evals/component/record_eval.py`, when `judge.mode == "live"`, register `metric.llm.client.on("completion:response", session.push_usage)` inside the session block, before scoring. The instructor client is the one `build_judge_llm` built (research R5). Nothing changes in `evals/ragas_llm.py`.
- [ ] T056 [US7] Run GATE (pytest, ruff and mypy as configured in `pyproject.toml`).

---

## Phase 10: Polish, compatibility, and release checks

**Purpose**: the hand-run live pass, docs, the `compat.yml` workflow, and the two final regression runs.

- [ ] T057 [P] Create `trustnoagent/live_check.py`, a hand-run live pass that is never run by pytest or CI and has no `__main__` block. Run with `uv run python -c "from trustnoagent.live_check import main; main()"`. `main()`:
  - requires `NVIDIA_API_KEY` (a clear `SystemExit` if absent);
  - scores one fresh record with all five built-ins plus one sample label rubric, using `JudgeConfig.from_env(mode="live")` and a `tempfile.mkdtemp()` `cache_dir`;
  - prints id, status, score or label, tokens and fingerprint;
  - re-runs and asserts the second pass made no uncached calls (via `cost.rows()`).
  - The docstring states the `uv sync --group calibration` prerequisite for `response_relevancy`.
- [ ] T058 [P] Add a "Per-record evaluation (v1.1.0)" section to `README.md` **after** the first code block and **below** `## Maintaining this repo`, so `tests/test_ci_config.py`'s README checks hold. It holds the `contracts/public-api.md` example and the five-row catalogue.
- [ ] T059 [P] Create `.github/workflows/compat.yml`, triggered on `pull_request`, with `permissions: contents: read` and **no credential of any kind** (`tests/test_ci_config.py` checks every workflow). One job:
  1. `actions/checkout@v4` with `fetch-depth: 0`, then `astral-sh/setup-uv@v5`.
  2. Create `git worktree add ../base v1.0.0` and `../head HEAD`, and run `uv sync --frozen` in each.
  3. Set env: the committed `JUDGE_MODEL`/`GENERATOR_MODEL` values, `DEEPEVAL_TELEMETRY_OPT_OUT=YES`, `RAGAS_DO_NOT_TRACK=true`, `DEEPEVAL_DISABLE_DOTENV=1`.
  4. In `../base`, build one summary: `uv run python -c "from pathlib import Path; from trustnoagent import EvalSuite; import os; s=EvalSuite(os.environ['JUDGE_MODEL'], os.environ['GENERATOR_MODEL']).run(); s.save(Path('/tmp/summary.json'))"`.
  5. In each worktree, capture stdout plus `echo "exit=$?"` into `/tmp/<side>.txt` for:
     - `uv run python -m evals.cli record --dry-run`
     - `uv run python -m evals.cli report /tmp/summary.json --out-dir /tmp/<side>-report`
     - `uv run python -m evals.cli compare /tmp/summary.json /tmp/summary.json`
     - `uv run python -m evals.cli gate "$JUDGE_MODEL" "$GENERATOR_MODEL"`
  6. In each worktree, run `uv run python -m evals.cli calibrate && git diff --exit-code evals/thresholds.yaml`.
  7. `diff -u /tmp/base.txt /tmp/head.txt && diff -ru /tmp/base-report /tmp/head-report`.
  - Replace `report`'s printed paths (which differ by side) with a fixed placeholder via `sed` before diffing, and note why in a YAML comment.
- [ ] T060 Run GATE. It must stay green with `compat.yml` present, which proves `tests/test_ci_config.py` accepts it.
- [ ] T061 **Final: cache re-serialisation.** Run `uv run pytest tests/test_v1_compat.py tests/test_v1_compat_summary.py -v` and confirm:
  - every one of the ≥1,120 committed entries re-serialises byte-identically;
  - the `make_key` golden hash holds;
  - the `RunSummary` schema matches its snapshot;
  - offline `build_summary()` is 100% cached.
  - Also confirm `git status --short evals/.judge_cache` is empty: no evidence was written by this feature.
- [ ] T062 **Final: run `compat.yml`.** First run its step sequence locally in two `git worktree`s (quickstart §6) and confirm zero diff. Then, **after confirming with the user**, since pushing is outward-facing, push the branch and open a draft PR so `compat.yml` runs in CI. Confirm the `compat` and `offline` jobs are both green.
- [ ] T063 [P] Walk through [quickstart.md](quickstart.md) §1–§6 and fix any command or expected output that drifted. Update `spec.md` **Status** to "Implemented".
- [ ] T064 Final GATE, then the CONSTITUTION.md Definition of Done:
  - suite green offline, `$0.00`, full hit rate;
  - separation contract intact;
  - ruff and mypy clean;
  - no module over 60 lines;
  - a negative test exists for all five built-ins and the rubric;
  - `tests/test_harness_integrity.py` passes.

---

## Dependencies & execution order

### Phase dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)**, which blocks all stories.
- **US1 (Phase 3)** depends on Phase 2. **Every later story depends on US1's facade and layer modules** (T026–T028), because they all route through `evaluate()`.
- **US2, US3, US4 and US5** depend only on US1 and are independent of each other. All four edit `trustnoagent/evaluators.py`, so run them in sequence or merge carefully; their test tasks can be written in parallel.
- **US6** depends on US5, since its live test needs `judge_env` and the live-key check (T048 and T049).
- **US7** depends on US5 for the same reason, and on US3's `ImportError` mapping.
- **Polish (Phase 10)** depends on every story.

### Story dependency graph

```text
Setup → Foundational → US1 ─┬─ US2
                            ├─ US3 ───────────┐
                            ├─ US4            │
                            └─ US5 ─┬─ US6    │
                                    └─ US7 ◄──┘
                                          └──→ Polish
```

### Within each phase

1. Test tasks, all [P], are written first and fail. Guards T003 and T004 pass immediately.
2. [P] implementation tasks in different files run in parallel.
3. Tasks editing the same file run in ID order.
4. GATE closes the phase.

## Parallel examples

```text
# Phase 2 tests, all at once:
T003 test_v1_compat.py   T004 test_v1_compat_summary.py   T005 test_contract_types.py
T006 test_judge_config.py   T007 test_fingerprint.py   T008 test_cache_location.py   T009 test_cache_session.py

# Phase 2 implementation, independent files:
T010 contract.py   T011 judge_config.py   T012 fingerprint.py   T013 location.py   T014 session.py
# then T015 store.py (needs T013, T014), T016 outcomes.py (needs T010), T017 support helpers

# US1:
T019 ragas_v1 test   T020 refusal_v1 test   T021 surface test
T022 ragas_adapter   T023 deepeval_adapter   T024 json_completion
# then T025 → T026, T027 → T028 → T029

# US4:
T040 rubric definition test   T041 rubric path test   T042 rubric.py   T043 rubric_judge factory
```

## Implementation strategy

- **MVP = Phases 1–3 (US1).** Five evaluators score caller records offline, reproducing v1 exactly. Stop, run GATE and T061, and demo.
- **Increment 2 = US2 + US3.** Discovery, and statuses in place of exceptions. The three P1 stories are complete.
- **Increment 3 = US4 + US5 + US6.** Rubrics, config-governed calls, fingerprint enforcement.
- **Increment 4 = US7 + Polish.** Real Ragas tokens, the live pass, `compat.yml`, the release checks.
- **Release:** v1.1.0 is tagged only after T062's `compat` job is green and T064's Definition of Done holds.

## Notes

- 64 tasks. Test-writing tasks precede implementation in every phase. Every phase ends with a GATE task.
- **Risk to watch:** T019. If `single_turn_score` renders prompts differently from `evaluate()`, committed evidence will miss. The contingency is written into T026.
- **Constitution check:** `CONTRACT_MODULES` in `tests/test_article_ii_facade.py` must list every framework-free module this feature adds under `evals/` (T016 names the one likely addition).

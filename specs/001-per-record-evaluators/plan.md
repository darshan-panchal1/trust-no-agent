# Implementation Plan: Per-Record Evaluator Contract

**Branch**: none; the spec was written on `main`. Create a feature branch before implementing. | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-per-record-evaluators/spec.md`, plus the `/speckit-plan` guidance of 2026-09-26.

## Summary

Add a synchronous `evaluate(evaluator, record, judge=None, cache_dir=None) -> EvalResult` next to the untouched v1.0.0 API. It scores one caller-supplied record with one named evaluator. v1.1.0 ships:
- four Ragas evaluators: `tna.ragas.faithfulness`, `tna.ragas.context_recall`, `tna.ragas.context_precision`, `tna.ragas.response_relevancy`;
- one DeepEval evaluator: `tna.deepeval.refusal_correctness`;
- caller-defined rubric judges, `tna.judge.<name>`.

Every result carries a status, a judging fingerprint and its provenance, token counts, and a raw audit payload. Nothing raises, and nothing is silently zero.

**Technical approach**:
- **One named routing facade.** `trustnoagent/evaluators.py`, permitted by the new Article II.c, dispatches by id to one per-layer evaluator module under `evals/component/` or `evals/behavior/`.
- **Reuse, not forks.** Those modules reuse the existing judge paths unchanged: `build_metrics`/`build_judge_llm`, `build_refusal_correctness_metric`, `CachedJudge` and `json_completion`.
- **One door for cache behaviour.** Cache-directory selection, fingerprint stamping and checking, and Ragas token capture all happen at the store (`read_or_raise`/`read_or_call`), through two small context-scoped modules. When no session is active, the store behaves exactly as in v1.0.0.

The research notes ([research.md](research.md)) record the verified library behaviour behind each choice.

## Technical Context

**Language/Version**: Python 3.12, exact (Article IX; `.python-version`)

**Primary Dependencies**: the existing exact pins only: ragas 0.4.3, deepeval 4.2.0, instructor 1.16.0 (transitive via ragas, used through ragas' own client), openai 2.54.0, pydantic 2.13.5 (provides `Field(exclude_if=...)`), and httpx (transitive via openai; used only in tests, through `MockTransport`). No new dependency. No version changes.

**Storage**: the existing file-per-key JSON evidence store. The directory is caller-supplied, or the committed `evals/.judge_cache/` inside a repo checkout.

**Testing**: pytest (offline, `--disable-socket`); ruff; mypy --strict. Live NIM verification is a hand-run live pass (R11). The CLI byte-identity check is the `compat` workflow (R12).

**Target Platform**: library on CPython 3.12. CI runs on ubuntu-latest via uv.

**Project Type**: Python library with an operator CLI. This feature adds library surface only.

**Performance Goals**:
- The offline suite keeps Article III's budget: a re-run costs $0.00 and finishes in under 10 s.
- A single offline `evaluate()` on a cache hit takes well under 1 s.

**Constraints**:
- Every module is at most 60 lines (Article VII).
- No async and no plugin system (Article X).
- The cache key is unchanged (Article III).
- v1.0.0 behaviour is byte-identical (FR-036/037).

**Scale/Scope**: 5 built-in evaluators (all of v1's scored metrics) plus rubrics, about 13 new modules (each ≤60 lines), 7 modified files, 1 new workflow, and a version bump to 1.1.0.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

The constitution is the repo root `CONSTITUTION.md`. No `.specify/memory/constitution.md` exists.

| Article | Gate | Pre-design | Post-design |
|---|---|---|---|
| 0: Prime Contract | Cold clone, no key, offline suite green, $0.00 | ✅ Nothing new is required on that path | ✅ New tests are offline; the live pass sits outside pytest |
| I: Evals are tests | No new entry point; no `__main__` | ✅ | ✅ `live_check.main()` follows the existing `live_pass.py` pattern (no `__main__` block) |
| I.a: One operator CLI | The suite never imports or invokes `evals/cli.py` | ⚠️ A pytest CLI regression test would violate it | ✅ The CLI half moves to the `compat.yml` workflow (R12) |
| II: Two layers | component ↛ behavior; no unified score; no spanning abstraction | ❌ A single `evaluate(id)` across both is forbidden | ✅ **Amended**: II.c (Eleventh amendment, applied 2026-09-26) names the facade by path; `tests/test_article_ii_facade.py` enforces it (passes, and fails when a probe violation is added) |
| II.b: Adapters | One framework per adapter, plus framework-free inputs | ⚠️ `evals.contract` import not covered | ✅ **Amended**: the text names `evals/golden/`, `app.models` and `evals/contract.py` |
| III: Determinism budget | Key unchanged; three `call_kind` forms; no sampling params; offline miss names the key | ✅ | ✅ The fingerprint sits beside the key (R2); the rubric uses `deepeval:judge.<name>`; mismatches are refused, never served |
| III.a: No outbound calls | Telemetry opt-outs; socket guard | ✅ | ✅ Live-mechanics tests use `MockTransport` under `socket_disabled` |
| IV: Failure demonstrable | Separation contract unaffected | ✅ | ✅ The old path is untouched |
| V: Thresholds are data | No thresholds read or written by the new path | ✅ | ✅ |
| VI / VI.a: No network; one door | No real client offline; `base_url` constant; one door per judge | ✅ | ✅ Clients are built only at the three existing sites; `JudgeConfig.base_url` is the constant |
| VII: Screen-readable | ≤60 lines per module | ⚠️ `store.py` is at 58 | ✅ Hooks are inlined, taking it to exactly 60 (R16) |
| VIII: Cost transparency | Every served call is accounted | ✅ | ✅ All calls pass through `store._record`; no fabricated USD |
| IX: Stack | Exact pins; Python 3.12; no new deps | ✅ | ✅ Only the project version changes (1.0.0 → 1.1.0) |
| X: Out of scope | No async, plugins, UI or provider layer | ✅ | ✅ Sync API; dict registry by import; stateless rubrics |
| XI: Trust the harness | A negative test per metric; no `run_async` | ✅ | ✅ Negative tests are planned for all five built-ins and the rubric; `measure()` is called directly, not through `assert_test` |

**Result: PASS after the Eleventh amendment.** The amendment is applied in this phase, not left pending:
- `CONSTITUTION.md` has the sync report, the II.b text, II.c, and the history entry.
- `tests/test_article_ii_facade.py` is added: `uv run pytest tests/test_article_ii_facade.py tests/test_constitution.py tests/test_module_size.py` gives 8 passed, and ruff and mypy are clean.

## Deviations from the planning guidance (each justified in research.md)

1. **Live NIM tests are a hand-run live pass, not a pytest marker** (R11). `conftest.py` strips `NVIDIA_API_KEY` at import (Trap 28), and a test asserts that it is absent. A marker-gated test would skip forever.
2. **The CLI byte-identity check is the `compat.yml` workflow, not a pytest test** (R12). Article I.a forbids the suite invoking the CLI, and `calibrate` rewrites thresholds. The in-suite half, `tests/test_v1_compat.py`, covers the cache, the key, the schema, and full cache coverage.
3. **Mode lives on `JudgeConfig`** (R7). This keeps `Evaluator.evaluate(record, judge)` exactly as requested.
4. **The stored fingerprint is the configuration fingerprint.** The result fingerprint keeps the requested formula, including the rendered prompt (R2). Storing the per-record value would produce false mismatches on Ragas entries shared across records.
5. **The fingerprint's template version is not `evaluator.version`** (R3). Otherwise every package release would invalidate every stored fingerprint.
6. **`cache_dir` is a public parameter, applied through a context override inside the store** (R1). An existing test pins `read_or_raise(key)`'s signature.
7. **Rubrics are passed as definitions, and `list_evaluators(*rubrics)` lists them** (R15). There is no global registry.
8. **The amendment also covers the `Evaluator` protocol and the contract modules**, because Article II's Forbidden clause names "protocol". It also aligns II.b's text with the imports the adapters already have.
9. **All five of v1's scored metrics ship** (corrected 2026-09-26 from two). The per-record path covers every metric `EvalSuite.gate()` gates on (`faithfulness`, `context_recall`, `RefusalCorrectness`), plus the two diagnostic Ragas metrics.
10. **No USD ceiling on the new path** (FR-035, R17).

## Project Structure

### Documentation (this feature)

```text
specs/001-per-record-evaluators/
├── spec.md              # clarified 2026-09-26
├── plan.md              # this file
├── research.md          # Phase 0: R1–R18
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── public-api.md    # trustnoagent exports, v1.1.0
│   └── cache-entry.md   # on-disk entry format, v1 compatible
├── checklists/requirements.md
└── tasks.md             # Phase 2, produced by /speckit-tasks (not created here)
```

### Source code (repository root)

```text
evals/
├── contract.py              NEW  Evaluator Protocol, EvalRecord, EvalResult, EvaluatorInfo, literals
├── judge_config.py          NEW  JudgeConfig + from_env(mode)
├── fingerprint.py           NEW  config/result fingerprints over canonical JSON
├── outcomes.py              NEW  EvalResult builders: skipped/error/invalid/ok-from-session
├── rubric.py                NEW  RubricJudge, prompt rendering, verdict model (framework-free)
├── cache/
│   ├── store.py             MOD  CacheEntry.fingerprint (exclude_if None); inline hooks (58 → 60)
│   ├── location.py          NEW  directory override + default_cache_dir()
│   └── session.py           NEW  judging session: observe / stamp / push_usage; FingerprintMismatch
├── adapters/
│   ├── ragas_adapter.py     MOD  + record_to_sample(EvalRecord)
│   └── deepeval_adapter.py  MOD  + record_to_test_case(EvalRecord)
├── component/record_eval.py NEW  tna.ragas.{faithfulness,context_recall,context_precision,
│                                  response_relevancy}: one table over matrix.METRIC_NAMES (ragas only;
│                                  the table splits into record_metrics.py if it nears 60 lines)
├── behavior/record_eval.py  NEW  tna.deepeval.refusal_correctness (deepeval only)
├── behavior/rubric_eval.py  NEW  tna.judge.<name> via CachedJudge  (deepeval only)
└── judge/json_completion.py MOD  RESPONSE_FORMAT constant (behaviour unchanged)
trustnoagent/
├── __init__.py              MOD  new exports; __version__ = "1.1.0"
├── env.py                   MOD  + judge_env(config); model_env unchanged
├── evaluators.py            NEW  Article II.c facade: REGISTRY, evaluate, list_evaluators
└── live_check.py            NEW  hand-run live pass (never pytest, never CI)
tests/
├── test_article_ii_facade.py  ADDED (this phase)
├── test_v1_compat.py          NEW  1,120-entry round-trip, key golden hash, schema snapshot, full coverage
└── test_per_record_*.py       NEW  registry, judge_config, statuses, reproduces_v1, rubric,
                                    fingerprint, live_mechanics (MockTransport)
.github/workflows/compat.yml   NEW  v1.0.0 vs HEAD CLI stdout and exit-code diff; calibrate diff
pyproject.toml / uv.lock       MOD  version 1.0.0 → 1.1.0 only (uv.lock line 2203)
CONSTITUTION.md                DONE Eleventh amendment
```

**Structure Decision**: this keeps the repo's existing layout.
- Framework-neutral contract code sits at `evals/` top level.
- Each framework's per-record evaluator sits in its own layer directory, which Article II's existing no-edge test already polices.
- The only cross-layer module is the named facade in the public `trustnoagent/` package.
- No existing module changes signature. `store.py`, the two adapters and `json_completion.py` gain additive code only.

## Implementation order (for /speckit-tasks)

1. **Contract.** `contract.py`, `judge_config.py`, `fingerprint.py`, `outcomes.py`, plus unit tests. These have no framework imports.
2. **Store.** Add `location.py` and `session.py`, then the `store.py` hooks and field. Add `tests/test_v1_compat.py` in the **same** step, so the 1,120-entry round-trip guards the change as it happens.
3. **DeepEval-side refusal evaluator**, and a test that it reproduces the v1 per-case score from committed evidence. Add its negative test on a v1 answer.
4. **Ragas-side evaluators, all four**, each with the same reproduction test and a negative test on a `v1_naive` answer. v1 already separates on `faithfulness` and `context_recall`, so their negatives come straight from committed evidence. Then usage pairing, with MockTransport live-mechanics tests.
5. **Rubric**: `rubric.py` and `rubric_eval.py`, with the pass/fail/invalid tests.
6. **Facade**, `judge_env` and exports; the statuses test across all failure classes.
7. **`compat.yml`**, run once on the PR, and the hand-run `live_check.py`.
8. **Version bump to 1.1.0** (`pyproject.toml`, `trustnoagent/__init__.py`, `uv lock --offline`). Then run the full DoD: suite, ruff, mypy, cost table at $0.00, compat green.

## Complexity Tracking

| Violation | Why needed | Simpler alternative rejected because |
|---|---|---|
| One module (`trustnoagent/evaluators.py`) reaches both eval layers | The spec's single entry point, with ids that name the framework | Two framework-specific entry points push framework knowledge onto every caller. Callers importing Ragas/DeepEval directly would bypass the one door and the evidence store, which is the failure this repo exists to expose. |
| Process-level judging session and directory override | Carries `cache_dir`, fingerprint and usage to the store without changing four signatures at the 60-line cap | Threading parameters breaks `test_read_or_raise_signature_accepts_no_call_function`, forks the judge factories, and pushes three modules over 60 lines. The state is safe because everything is synchronous (Article X), sessions cannot nest, and the state is restored in `finally`. |

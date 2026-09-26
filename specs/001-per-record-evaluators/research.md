# Phase 0 Research: Per-Record Evaluator Contract

**Feature**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Date**: 2026-09-26

Each entry below records the decision, the rationale, and the alternatives considered. Every library fact was checked against the pinned `.venv` on 2026-09-26: pydantic 2.13.5, instructor 1.16.0, ragas 0.4.3, deepeval 4.2.0. Probes ran offline against an `httpx.MockTransport`, never the network.

---

## R1. How the caller's cache directory reaches the existing store

**Decision.** Add a context-scoped directory override in a new module, `evals/cache/location.py`. `store.read_or_raise` and `store.read_or_call` resolve their directory at call time as "override if set, else `CACHE_DIR`". The facade sets the override for the duration of one `evaluate()` call. Neither function's signature changes.

**Rationale.**
- `tests/test_cache_store.py::test_read_or_raise_signature_accepts_no_call_function` pins `read_or_raise`'s parameters to exactly `["key"]`. A `cache_dir` parameter would break an existing test, which violates SC-009.
- New writer functions (for example, a `read_or_call_in(dir, …)`) would escape `tests/test_one_door.py`, which finds writers by the call name `read_or_call` and compares the set with `==`. The one-door rule would silently stop covering them.
- The override has the same shape as the mechanism the suite already relies on: `tests/conftest.py::isolated_cache` monkeypatches `store.CACHE_DIR`. Resolving at call time keeps that monkeypatch working.
- Everything is synchronous (Article X), so a process-level override set and restored around one call cannot interleave.

**Alternatives rejected.**
- Threading `cache_dir` through `CachedJudge`, `RagasCacheBackend` and `build_judge_llm`. All three sit at 59–60 of the 60 allowed lines, and it would change three signatures to carry one value.
- A new env var. The spec forbids it (FR-026, FR-032).

## R2. Where the fingerprint is stored, and what exactly is stored

**Decision.** Add an optional field to the existing entry model:

```python
fingerprint: str | None = Field(default=None, exclude_if=lambda v: v is None)
```

- The stored value is the **configuration fingerprint**: `sha256(canonical_json({judge_model, template: "<template_id>@<template_version>", decoding, schema}))`.
- The **result** fingerprint on `EvalResult.judge_fingerprint` follows the requested formula: `sha256(judge_model, template_id@version, rendered prompt, decoding params, schema)`. It is built as `sha256(config_fingerprint ‖ rendered_prompt_hash)`.

**Rationale.**
- **The serialisation stays byte-identical.** `exclude_if` exists in pydantic 2.13.5 (verified). When the field is `None`, `model_dump_json()` emits exactly the five v1 fields, so every old-path write stays byte-identical. Measured today: all 1,120 committed entries round-trip through `CacheEntry.model_validate_json(...).model_dump_json()` byte-for-byte. A test pins that this stays true.
- **Storing the per-record fingerprint would raise false mismatches.** Ragas renders its own internal prompts, and different records can produce the same internal prompt. `ResponseRelevancy`'s question-generation prompt depends only on the response (`ragas/metrics/_answer_relevance.py`), so two records with the same answer and different questions share a cache key. Storing the record-level fingerprint in that shared entry would make the second record look like a mismatch.
- **The configuration fingerprint covers exactly what the key cannot see.** The key already covers `call_kind`, the model and the prompt hash. The stored value adds the components that can change output without changing the key: decoding parameters, output schema, and template version.

**Alternatives rejected.**
- A sidecar file per key: two files per entry breaks Article III's "one JSON file per key".
- `exclude_none=True` on the whole model: it would also drop `usd: null`, which is common now that NIM is unpriced, and so change old-path bytes.

## R3. The fingerprint's template version is separate from `evaluator.version`

**Decision.** `evaluator.version = "<trustnoagent version>+<lib>@<lib version>"`, as specified, is reported but **not** used in the fingerprint. Each evaluator carries its own `template_version` for the fingerprint:
- `ragas@0.4.3/1` for Ragas evaluators;
- `refusal-steps/1` for RefusalCorrectness;
- for rubrics, a content hash of their instructions and label set or score range.

**Rationale.** If the package version fed the fingerprint, every patch release would make every stored fingerprint disagree. FR-030 would then turn each 1.1.x → 1.1.y upgrade into blanket `error` results. The template version moves only when the prompt, steps or schema move. For rubrics it is derived from their content, so it cannot be forgotten.

**Alternative rejected.** Using `evaluator.version` as the template version, which fails for the reason above.

## R4. Mismatch detection and provenance live in the store, via a judging session

**Decision.** A new module, `evals/cache/session.py`, holds an optional active *judging session*: the expected configuration fingerprint, the judge `call_kind`, a FIFO of pending usages, and the entries served. `store.py` makes two inline hooks, each a no-op when no session is active:
- **Read** (a hit in either function) calls `session.observe(key, entry)`. If a stored fingerprint differs from the session's, it raises `FingerprintMismatch(key, stored, expected)`. Otherwise it records the entry as served.
- **Write** calls `entry = session.stamp(call_fn())`. This sets the fingerprint and, for the judge `call_kind`, the next pending usage. It then observes the entry.

**Rationale.**
- Every judge call on both paths already passes through `read_or_raise` or `read_or_call`, so putting the hooks at that one door covers Ragas, GEval and rubric calls without touching `CachedJudge`, `RagasCacheBackend` or `build_judge_llm`.
- With no session active, the behaviour is exactly v1.0.0.
- Only `store.py` grows, by two net lines (58 → 60). The hooks are inlined into existing lines.

**Alternative rejected.** Adding `fingerprint=` and `served=` parameters to `CachedJudge` and `RagasCacheBackend`. That means three signature changes to modules at the line cap, and GEval is built through `build_refusal_correctness_metric → build_geval_metric`, so it would need a third layer of pass-through.

## R5. Real Ragas token counts

**Decision.** In live mode, the Ragas per-record evaluator registers `llm.client.on("completion:response", session.push_usage)` on the instructor client that `build_judge_llm` already built. `session.stamp` pairs each pending usage with the next write whose `call_kind` is the evaluator's judge kind (`ragas:faithfulness`, `ragas:context_recall`, `ragas:context_precision` or `ragas:response_relevancy`). `ragas:embeddings` writes are never paired.

**Verified.**
- **`RagasCacheBackend.set()` never sees usage.** The probe observed `set()` receive the parsed model with no `_raw_response` usage (`usage=None`), so capturing tokens inside the backend is not possible.
- **The instructor hook fires with real usage.** It delivered `CompletionUsage(prompt_tokens=123, completion_tokens=45)` from the mocked NIM response, with no change to `build_judge_llm`.
- **Calls are sequential, for all four metrics.** For an `InstructorLLM`, ragas 0.4.3's `PydanticPrompt.generate_multiple` makes one synchronous `generate()` call and ignores `n` (`ragas/prompt/pydantic_prompt.py`). Faithfulness makes its statement and verdict calls one after the other. Context precision loops `for context in retrieved_contexts` (`_context_precision.py:148`), awaiting each call. Every call is sync inside ragas' cacher, with no await between the hook firing and the write, so FIFO pairing is exact even when several judge calls share one `call_kind`.
- **The old path is untouched.** No session means no hook and no stamping, so `set()` keeps writing 0/0 (FR-037).

**Alternative rejected.** An `httpx` event hook on the OpenAI client. It would need `build_judge_llm` to accept an `http_client`, which is a signature change in a 60-line module, for the same information.

## R6. How result token totals are computed

**Decision.** `tokens_in` and `tokens_out` are summed over the **distinct judge-`call_kind` cache keys** served during the evaluation. If any contributing entry records 0/0 (a pre-1.1 Ragas entry), both are `None` (unknown).

**Rationale.** Summing distinct keys makes a live first call and its cached repeat report identical tokens (SC-005). Returning unknown rather than a partial sum means a result never under-reports while looking exact (FR-034).

## R7. Offline/live mode lives on `JudgeConfig`

**Decision.** `JudgeConfig(mode=...)` and `JudgeConfig.from_env(mode="offline")`.

**Rationale.** The requested protocol is exactly `evaluate(record, judge) -> EvalResult`. Mode has to reach the evaluator, and the judge configuration already answers "how is this judged". `EvalSuite(mode=...)` is unchanged.

**Alternatives rejected.**
- A third `evaluate` parameter, which changes the requested signature.
- Evaluator instances bound to a mode, which doubles the registry.

## R8. Applying `JudgeConfig` to the existing call paths

**Decision.** A new context manager, `judge_env(config)` in `trustnoagent/env.py`, sets `JUDGE_MODEL` and `GENERATOR_MODEL`, and also `NVIDIA_API_KEY` when the config carries one, for the duration of one call. It then restores the previous values. This mirrors `model_env`, which `EvalSuite` already uses, and leaves `model_env` itself unchanged.
- `api_key` is declared with `field(repr=False)`, so a result, log line or assertion diff can never print it.
- `base_url` is `evals.models.NIM_BASE_URL`. `from_env()` never reads an env var for it (FR-025).

**Rationale.** The three existing client construction points keep reading their values exactly as they do today; nothing forks. A caller who builds `JudgeConfig` by hand still governs the call.

## R9. Rubric judges reuse `CachedJudge` and `json_completion`

**Decision.**
- The rubric evaluator renders its prompt with the framework-free `evals/rubric.py`, then calls `CachedJudge("deepeval:judge.<name>", mode).generate(prompt)`. That call goes through the existing `json_completion`, so the NIM request uses `response_format={"type": "json_object"}` and one retry.
- The text that comes back is validated with a pydantic model built from the definition: `{"label": <one of labels>, "reason": str}` or `{"score": <min..max>, "reason": str}`.
- `call_kind` is `deepeval:judge.<name>`, which is Article III's existing `deepeval:<metric>` form. There is no fourth form.

**Failure mapping.**
- **The model never returns valid JSON.** `json_completion` raises `json.JSONDecodeError` after two attempts. The result is `invalid_output`, with `raw` holding the model's text (`exc.doc`). Nothing is cached, because the write only happens after a successful call.
- **Valid JSON that fails the rubric's validation.** It is cached as returned, and re-validation produces `invalid_output` deterministically on every re-run (SC-005, SC-006).

**Alternative rejected.** GEval for rubrics. It produces only a 0–1 score and cannot carry a label set.

## R10. Mapping failures to statuses

| Signal | Status | Reason text |
|---|---|---|
| A required field is absent on the record | `skipped` | Names the field. No judge call is made. |
| Unknown id, or a bare `"tna.judge.*"` string | `error` | Names the id and the expected form. |
| `JUDGE_MODEL`/`GENERATOR_MODEL` unset (`judge=None`) | `error` | The existing accessor message, naming the variable. |
| Live mode with no API key | `error` | Names `NVIDIA_API_KEY`. Checked before any client is built. |
| No `cache_dir` outside a repo checkout | `error` | Asks for a directory. |
| `CacheMiss` offline | `error` | Names the key, and says new records need live mode. |
| `FingerprintMismatch` | `error` | Names both fingerprints; stored raw text kept. |
| `ImportError` (live embeddings, no `calibration` group) | `error` | Names `uv sync --group calibration`. |
| NaN from any Ragas metric | `invalid_output` | Verified branches in ragas 0.4.3: `_answer_relevance.py` (all generated questions empty), `_faithfulness.py:192/211/262` (no statements or verdicts), `_context_recall.py:118` (zero denominator), `_context_precision.py:116` (no verdicts). |
| Ragas output parser error, or pydantic `ValidationError` | `invalid_output` | Raw text kept. |
| GEval `ValueError` from `trimAndLoadJson` ("outputted an invalid JSON") | `invalid_output` | Raw text kept. |
| `json.JSONDecodeError` from `json_completion` | `invalid_output` | Raw = `exc.doc`. |
| Any other `Exception` | `error` | Type and message. This is the facade's safety net (FR-004). |

`single_turn_score` re-raises the metric's exception (ragas 0.4.3, `metrics/base.py`), so each adapter sees the real exception type.

## R11. Live NIM verification cannot be a pytest test here

**Finding.**
- `conftest.py` removes `NVIDIA_API_KEY` from `os.environ` at import time (Trap 28: DeepEval autoloads `.env` before any hook can run).
- `tests/test_provider_credentials.py` asserts that the key is absent in every run.

A pytest test marked `live` and "skipped without `NVIDIA_API_KEY`" would therefore skip on every invocation, including `-m live` with `EVAL_LIVE=1`. That is permanent decoration, which Article XI names as "not evidence".

**Decision.**
- Live verification is a hand-run live pass, `trustnoagent/live_check.py`, following the existing `evals/*/live_pass.py` pattern: `uv run python -c "from trustnoagent.live_check import main; main()"`. It never runs under pytest or in CI, and it writes only to a caller-supplied temporary cache directory.
- Live-mode *logic* (token pairing, fingerprint stamping, write paths, failure mapping) is unit-tested offline under `socket_disabled`. The tests use an `openai.OpenAI` backed by `httpx.MockTransport`, the same technique used for the R5 probe. They inject it by monkeypatching the `openai.OpenAI` name inside `evals.ragas_llm` and `evals.judge.cached`, and pass the credential through `JudgeConfig(api_key=...)`, never through the process environment.

**Alternative rejected.** Making `conftest.py` keep the key when `EVAL_LIVE=1`. That reopens Trap 28 (a `.env` credential leaking into a run) and changes v1.0.0 behaviour.

## R12. The byte-identical CLI regression runs in a workflow, not pytest

**Finding.**
- Article I.a says the suite "never imports or invokes" `evals/cli.py`, and `tests/test_constitution.py` enforces the import half.
- `calibrate` rewrites `evals/thresholds.yaml`. A pytest node doing that is exactly the hazard Article I.a exists to prevent.
- A non-dry-run `record` is live and billed.

**Decision: the CLI half.** A new workflow, `.github/workflows/compat.yml`, runs on `pull_request` with no credentials. `tests/test_ci_config.py` already polices every workflow file by directory listing. The workflow:
1. Makes two worktrees: `v1.0.0` (tag `711dc26`) and the PR head. Each gets `uv sync --frozen` and the committed `JUDGE_MODEL`/`GENERATOR_MODEL`, plus the three telemetry opt-outs, set exactly as `action.yml` sets them.
2. Builds **one** summary at `v1.0.0` offline with `EvalSuite(...).run().save(...)`, so the timestamp is fixed, and feeds that same file to both sides.
3. On each side, runs `record --dry-run`, `report <summary>`, `compare <summary> <summary>` and `gate <judge> <gen>`, capturing stdout and the exit code of each.
4. Runs `calibrate`, then `git diff --exit-code evals/thresholds.yaml`.
5. Diffs the two sides byte-for-byte and fails on any difference.

**Decision: the in-suite half**, which Article I.a allows. `tests/test_v1_compat.py`, split if it exceeds the line cap, asserts that:
- every committed entry validates and re-serialises byte-identically;
- `make_key` returns a pinned golden hash for a fixed triple;
- `RunSummary.model_json_schema()` equals a committed snapshot;
- an offline `build_summary()` raises no `CacheMiss` and every cost row is 100% cached. It **fails** rather than skipping, unlike the fixtures that skip on a miss.

## R13. Detecting a repo checkout

**Decision.** `location.default_cache_dir()` returns `CACHE_DIR` when both `.git` and `pyproject.toml` exist at `CACHE_DIR.parents[1]` (the repo root). A worktree's `.git` is a file, which `exists()` still accepts. Otherwise it returns `None`, and the facade answers `error`.

**Rationale.** The wheel ships `evals/.judge_cache/` inside site-packages (verified 2026-09-12 in `pyproject.toml`'s notes), and site-packages has no `.git`. So an installed package never silently writes caller records into itself (FR-032).

## R14. Evaluator versions without `importlib.metadata`

**Decision.**
- Each per-layer module exports a library string built from the imported package: `f"ragas@{ragas.__version__}"` or `f"deepeval@{deepeval.__version__}"`. Both attributes exist and equal the pins (0.4.3 and 4.2.0, verified).
- The facade composes `f"{trustnoagent.__version__}+{LIB}"`.
- A test parses `pyproject.toml` with `tomllib` and asserts both strings match the exact pins.

**Rationale.** `importlib.metadata` is off the table for this feature. The facade can't import a framework (II.c), so the library version has to come from the layer module.

## R15. Rubric judges are passed as definitions, not registered

**Decision.**
- `evaluate()` accepts `str | RubricJudge`.
- `list_evaluators(*rubrics)` returns the built-ins plus any rubrics passed in.
- There is no process-wide rubric registry.

**Rationale.**
- No global mutable state to leak between tests or callers.
- No "already registered" failure mode.
- Article X's plugin ban is honoured in spirit as well as letter.
- Built-in ids still resolve from a plain dict filled by direct import, as requested.

## R16. Module-size budget (Article VII: 60 lines)

| File | Now | After | How |
|---|---|---|---|
| `evals/cache/store.py` | 58 | 60 | Field line and one import. Hooks go inline on the existing `path =`, `return _record(...)` and `entry = ...` lines. |
| `evals/judge/json_completion.py` | 30 | 31 | `RESPONSE_FORMAT` constant, used by both the call and the fingerprint. |
| `trustnoagent/env.py` | 30 | ≤50 | Adds `judge_env`. |
| `trustnoagent/__init__.py` | 13 | ≤25 | New exports and `__version__ = "1.1.0"`. |
| `evals/adapters/ragas_adapter.py` | 20 | ≤35 | Adds `record_to_sample`. |
| `evals/adapters/deepeval_adapter.py` | 30 | ≤45 | Adds `record_to_test_case`. |
| New modules | — | ≤60 each | Split wherever a module approaches the cap. |

## R17. Rejected: a USD ceiling on the new path

**Decision.** None is added (spec FR-035).

**Rationale.** NIM has no dated price (Article VIII, §V8.6), so `usd` is `None` for every live call. A ceiling would be inert, as `record --allow-unpriced` already documents. The controls are explicit live mode and the credential. Cost accounting still happens, per `call_kind`, through the store.

## R18. Rejected: `nvext.guided_json`

**Decision.** It is not adopted. Rubric calls keep `response_format={"type": "json_object"}` through the existing `json_completion`, as instructed.

**Consequence.** Structure is enforced after the call, by pydantic, and surfaces as `invalid_output`. Adopting `guided_json` later changes only the fingerprint's `decoding` and `schema` components, not the key. The configuration-fingerprint check would then refuse stale entries rather than serve them.

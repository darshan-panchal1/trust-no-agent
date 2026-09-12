<!--
SYNC IMPACT REPORT — Tenth amendment, 2026-09-09
Ordinal step: Ninth → Tenth. This document tracks changes as dated ordinal amendments and
has never carried a semver line; none is introduced here. Under semver this step would be
MAJOR — the required credential changes, which breaks every existing setup. Same
classification the Eighth carried, and for the same reason.
Modified: Article III (temperature and logprobs evidence clauses re-sourced; the rules
  themselves unchanged), Article VI.a (NVIDIA_API_KEY as the sole credential; the eager
  client is now openai.OpenAI against a NIM base_url; new base_url clause), Article VIII
  (Groq's absent price table → NIM's), Article IX (direct imports are pinned explicitly).
Added: no new articles. One new clause in VI.a (base_url) and one in IX (direct-import
  pinning). Removed: no articles, no rules.
Unchanged on purpose: Article III's env-var/accessor paragraph, already provider-neutral —
  it names no vendor and needed no edit. Article III's Trap 19 clause ("predates the move
  to Groq"), which stays true after this amendment and is dated evidence about ragas' key
  derivation, not about a provider. Article X:330's no-provider-switch line, which a clean
  replacement satisfies; nothing here makes two providers reachable at runtime.
First amendment with a non-zero cost: 149 of 191 recorded cache entries are invalidated.
  Preserved at commit 4584441, committed immediately before this amendment for that purpose.
Deferred (not governance, tracked in the amendment entry): the three call-site migrations,
  pyproject.toml's groq/openai pins and Groq model IDs in the pytest env block,
  live.yml's GROQ_API_KEY secret, and pricing.yaml's Groq-era rows.

Prior report — Ninth amendment, 2026-09-08
Ordinal step: Eighth → Ninth. Under semver this step would be MINOR — a rule is added and
guidance expanded; no principle is removed or redefined.
Modified: Article VI (Forbidden clause gains a scope clarification, its existing sentence
  unchanged), Article VI.a (GROQ_API_KEY stated as the only credential on any path; the
  offline no-real-provider rule extended to the embeddings provider), Article IX (new
  dependency-group rule for sentence-transformers/torch).
Added: no new articles. Removed: no articles.
Unchanged on purpose: VI.a's OPENAI_API_KEY-absent assertion, which guards DeepEval's
  implicit-provider hazard and has nothing to do with embeddings — it now holds on every
  path, not only the offline suite.
Deferred (not governance, tracked in the amendment entry): evals/embeddings.py's migration,
  the pyproject.toml calibration group, pricing.yaml's text-embedding-3-small row,
  tests/test_embeddings.py, and tasks.md's stale OPENAI_API_KEY references.

Prior report — Eighth amendment, 2026-09-08
Ordinal step: Seventh → Eighth. Under semver this step would be MAJOR — a fixed model pin
is removed and two required environment variables replace it.
Modified: Article III (judge pin → JUDGE_MODEL/GENERATOR_MODEL selection; coarse-scoring
  cause restated provider-neutrally; sampling-parameter rationale replaced), Article IV
  (generator pin → GENERATOR_MODEL), Article VI.a (eager Groq construction; evals/judge.py
  → evals/judge/), Article VIII (UNVERIFIED USD column), Article X (env-var selection is
  not a provider abstraction layer), Article XI (evals/judge.py → evals/judge/).
Preserved as dated evidence: the Trap 19 sonnet/opus key measurement, V3.5's coarse-scoring
  finding, and Article VIII's $3/$15-vs-$2/$10 example — all Anthropic-derived, all still
  proving provider-neutral rules.
-->

# CONSTITUTION — `trust-no-agent`

**Purpose.** This repository exists to prove one claim on camera: *an LLM agent can produce output that reads as correct and still be measurably broken.* Every file here is either evidence for that claim or the scaffolding that makes the evidence reproducible. Code that is neither does not belong.

**Audience.** One viewer. A laptop. No API key. Ten minutes.

These principles are non-negotiable. They are not defaults, not preferences, and not subject to being traded away for convenience during implementation. Violating code is wrong even when it works.

---

## Article 0 — The Prime Contract

A stranger who has never seen this repo runs:

```
git clone <repo> && cd trust-no-agent && uv sync && uv run pytest
```

Within ten minutes on a cold machine, with no API key and no configuration, they see the v2 suite pass and the v1 suite fail, having spent $0.00.

**Article 0 outranks every article below it.** When a principle collides with the Prime Contract, the contract wins and the principle is amended in the open — never violated in silence. When two articles below collide, precedence is: **VI → III → XI → IV → I → VII → II → V → VIII**.

---

## Article I — Evals Are Tests

**Rule.** Every eval is a pytest test. `pytest` is the only command a viewer must learn.

- Each golden case is its own test node via `pytest.mark.parametrize`. One broken case fails one node, not the suite.
- Node IDs name the metric and the case, so the failure line is the diagnosis: `test_faithfulness[v1-refund_window]`.
- Markers are the only dimension of selection: `ragas`, `deepeval`, `live`.
- The README's first code block is `uv run pytest`. Any other invocation shown to a viewer is a bug in the README.

**Enforced by.** A test asserting the repo contains no module with an `argparse`/`click` import or an `if __name__ == "__main__"` block outside `app/` and the single path named in I.a.

**Forbidden.** `run_evals.py`. `scripts/`. A `Makefile` target that does anything but shell to `pytest`. A notebook that must be run in order. Any wrapper whose reason for existing is "pytest output is hard to read" — fix the reporting, not the entry point.

### I.a — Exactly one operator CLI

`calibrate`, `record`, `compare` and `report` produce and diff data. They are not evals, and routing them through pytest would make pytest the thing that rewrites `evals/thresholds.yaml` — a test that edits its own pass criteria. **Exactly one module, `evals/cli.py`, may import `argparse`/`click`.**

- **The test suite never imports or invokes it.** A test asserts no module under `evals/component/`, `evals/behavior/` or `tests/` imports `evals.cli`.
- It never runs in the default CI job.
- `pytest` remains the only command a viewer must learn. The README's first code block is still `uv run pytest`; CLI commands appear only under a "maintaining this repo" heading, below the fold.
- Article I's enforcement test carves out this **single path by name, not by pattern.** A pattern admits `evals/cli_helpers.py` tomorrow.

**Cost.** A viewer reading the whole repo finds one entry point that is not `pytest`. Accepted, because the alternative is a pytest node whose side effect is rewriting the thresholds that every other node asserts against — which Article V exists to prevent.

---

## Article II — Two Layers, Never Merged

**Rule.** Two frameworks answer two different questions, and the tutorial's whole pedagogical point is that these questions are different.

| | Ragas — `evals/component/` | DeepEval — `evals/behavior/` |
|---|---|---|
| Question | *Why is it bad?* | *Is it bad enough to fail?* |
| Output | Scalar diagnostics | Pass/fail verdicts |
| Scope | Retrieval + generation quality (faithfulness, answer relevancy, context precision, context recall) | Assertion gates and agent-trajectory metrics (task completion, tool correctness, G-Eval criteria) |

- The two packages share exactly one thing: `evals/golden/`, which loads the dataset into plain, framework-free dataclasses. Each layer adapts those to its own framework's types in a module that speaks to that framework and no other — colocated under `evals/adapters/` per II.b.
- `evals/component/` may not import `evals/behavior/`, and vice versa. Neither may import the other's framework.

**Enforced by.** A banned-import rule plus a test asserting the module graph has no edge between the two packages.

**Forbidden.** A Ragas metric registered as a DeepEval custom metric. A DeepEval assertion consuming a Ragas score. A "unified score." A base class, protocol, or adapter layer spanning both. Two golden datasets.

### II.a — `ToolCorrectnessMetric` is demonstrative, not a gate

`ToolCorrectnessMetric` stays in the repo, **at library defaults**, and is **explicitly not one of the metrics that separates v1 from v2** under Article IV's separation contract. It is shipped to be looked at, not to be trusted.

At defaults it is **unordered recall over `expected_tools`**: each expected tool is greedily matched on `(name, type)`, the score is `Σ matches / len(expected_tools)`, order is ignored, and **extra called tools are not penalised at all**. An agent that makes every correct call plus a pile of spurious ones scores a clean **1.0**.

`should_consider_ordering=True` does not fix this. It divides a weighted longest-common-subsequence by `len(expected_tools)` — the denominator still ignores what was actually called, so extras remain free.

Only `should_exact_match=True` penalises extra calls, and it does so by being binary and positional: any reorder returns 0.0. **We do not ship it as a gate.** A metric that cannot tell "called an extra tool" from "called the right tools in a different order" is not a pass/fail instrument.

Measured on the installed version — the numbers are in `docs/api-notes.md`, Verification 2:

| called | expected | default | `should_consider_ordering` | `should_exact_match` |
|---|---|---|---|---|
| `[a, b]` | `[a, b]` | 1.0 | 1.0 | 1.0 |
| `[a, b, c]` | `[a, b]` | **1.0** | **1.0** | 0.0 |
| `[b, a]` | `[a, b]` | 1.0 | 0.5 | **0.0** |

**The repo ships all three configurations scored side by side**, in one place, so a viewer sees the same trajectory produce three different verdicts. That contrast is the lesson: a green tool-correctness number is a statement about a metric's configuration, not about an agent.

The metric's measured semantics — including this table — are restated in its **module docstring**. A reader must not have to leave the file to learn that the default does not penalise spurious calls.

### II.b — One adapter directory, one framework per module

Adapters for both frameworks **may** live in a single directory, `evals/adapters/`, subject to one condition:

- **Each adapter module imports from exactly one framework — ragas or deepeval, never both — plus `evals/golden/`.** That is the entire permission. There is no second exception, and no module may be added there that speaks to neither framework or to both.

**Why the directory moved, and why the rule did not.** The constraint this article exists to protect is **no cross-framework type leakage and no shared abstraction spanning both**. A directory boundary was only ever a proxy for that property, and a weak one: two modules in separate packages can still import each other, and separation by folder proves nothing a reader can rely on. **The property is enforced by import direction, not by physical directory separation.** Filing the two adapters side by side makes the one-framework-each rule visible in a single listing, where a reviewer can check it, instead of spreading it across two packages where only a graph walk would catch a violation.

**This does not loosen the Forbidden clause above.** What that clause targets is *one abstraction serving both frameworks* — a shared base class, a common protocol, a dispatcher that switches on framework. Two independent modules that each speak to exactly one framework are not that, however they are filed. **Colocation is not spanning.** A base class, protocol, or adapter layer bridging ragas and deepeval remains forbidden wherever it is placed, including inside `evals/adapters/`.

**Enforced by.** `tests/test_constitution.py`, over the module import graph rather than over filenames: **no module under `evals/adapters/` may have import edges to both frameworks**; `ragas_adapter` is reachable only from `evals/component/`, and `deepeval_adapter` only from `evals/behavior/`. A filename-based check would pass on a module that merely avoided saying `deepeval` in its own name.

**Cost.** A reader looking for one layer's adapter finds it one directory away from that layer rather than beside it. Accepted, because the enforcement moves from a convention a reviewer has to notice to an assertion that fails in CI.

---

## Article III — Determinism Budget

**Rule.** Judge calls are cached to disk and the cache is committed. A second run of an unchanged suite costs **$0.00** and finishes in **under 10 seconds**.

- Cache key: `sha256(call_kind || model_identity || prompt_hash)`. Nothing else. No timestamps, no run IDs, no paths, no ordering.
- `call_kind` takes one of three forms — `generate:<variant>`, `ragas:<metric>`, `deepeval:<metric>` — so one store holds generation and judging together and every entry announces what it is. A bare metric name cannot do this: generation calls have no metric, and inventing a pseudo-metric for them would make the field mean two different things depending on the row.
- `model_identity` is the full pinned model ID plus every request parameter that can change the call's output (effort level, system prompt version) — a judge's, when `call_kind` is `ragas:*` or `deepeval:*`; the generator's, when it is `generate:*`. Anything that moves the output moves the key, or the cache is lying.
- **That clause is not decorative, and one of our own libraries violates it.** Ragas' `cacher()` does not let a caller supply a key — it computes one, and that key **excludes model identity entirely**. It wraps the *bound* method `InstructorLLM.generate(self, prompt, response_model)`, so `self` — which carries the model, the client, the provider and the system prompt — is never visible to the key. Measured: the key for one prompt under `claude-sonnet-5` and under `claude-opus-5` is byte-identical, `495542df5379…` for both (`docs/api-notes.md`, Trap 19 / §V4.1). **That measurement predates the move to Groq and is kept in the provider's own names on purpose** — it is dated evidence, and the defect it proves is a property of ragas' key derivation, not of any provider. Accepting that key as our own would serve one judge's cached answers under a different judge's identity — a **green suite, a `$0.00` cost table, and every threshold calibrated against a judge that never ran.** It is the exact failure this repository was built to expose, arriving through the cache rather than the metric.
- **Therefore the `CacheInterface` implementation re-keys.** Ragas' computed key is accepted **only as the `prompt_hash` component** of the real key — never as the complete key. It is a legitimate prompt hash, a deterministic SHA-256 over function, prompt and response model; it is simply not a complete one. `call_kind` and `model_identity` are supplied by us, on the outside, so a judge change moves the key exactly as this article requires.
- One JSON file per key under `evals/.judge_cache/`, committed. One file per key so a cache refresh is a reviewable diff and merges cleanly.
- Each entry records the response, the token counts, and the USD cost at write time — Article VIII reads from here.
- **Miss behavior is mode-dependent.** Offline (default): hard failure naming the missing key and the exact command to refresh it. Live: call, record, write.
- **Determinism comes from the cache, not from sampling parameters.** `temperature`, `top_p`, and `top_k` must not appear anywhere in this repo. Do not write code that pretends to pin them. The original reason was that current Claude models reject them with a 400; under Groq that reason was already gone — `chat.completions.create` accepted `temperature` as an ordinary parameter (`docs/api-notes.md`, V5.3). **Both of those are dated provider measurements, and neither has been re-run against NIM:** Verification round 8 did not test whether NIM's endpoint accepts a sampling parameter, and this article does not assume it from the fact that the request schema is OpenAI-shaped. **The rule survives its rationale, and now matters more than it did:** a knob the provider rejects cannot silently widen the cache's blast radius, and a knob it accepts can — and a knob whose treatment nobody has checked is the worst of the three to leave reachable. A sampling parameter moves the output without moving the key unless it is part of `model_identity`, so this repo sets none. **This is now a policy choice, not a provider-enforced one, and it is enforced the same way VI.a's one-door rule is: at the single call-construction point for each `call_kind`** — the judge factory in `evals/judge/` for `ragas:*`/`deepeval:*`, the one generation call site for `generate:*` — none of which accept or forward a sampling parameter. The provider's own validation is no longer a backstop and was never the mechanism; it only used to fail loudly by coincidence.
- **Model identity is selected, not hardcoded.** The judge and the generator are named by two required environment variables, `JUDGE_MODEL` and `GENERATOR_MODEL`, each read through exactly one accessor function. **Neither accessor may supply a default** — no `os.environ.get(..., fallback)`, no `or "..."`. A missing variable is a hard error at first read, naming the variable that is missing. This is Article V's threshold discipline applied to model selection, and for the same reason: a silent fallback produces a cache key for a model nobody chose.
- **One accessor each, and exactly one.** A value the cache key derives from may not be declared in more than one place. Article VII's tolerance for duplication — boring and explicit beats DRY — does not extend to constants that determine key identity, because two copies that drift produce two different keys for the same call and neither is wrong on its face.
- **The default suite's values are committed** to the `env` block of `[tool.pytest.ini_options]`, Article III.a's mechanism, so Article 0's cold clone still needs no configuration and no API key. Anything running outside pytest — `evals/cli.py`, every live pass — must set them explicitly or fail. **A test asserts both are set at collection time**, because a silently-ignored `env` block is the exact failure III.a already documents: a setting that looks correct and does nothing.
- **`model_identity` derives directly from these two values.** `JUDGE_MODEL` moves every `ragas:*` and `deepeval:*` key; `GENERATOR_MODEL` moves every `generate:*` key. Changing either invalidates the affected half of the cache by design. That is the feature.
- **GEval's coarse scoring is a missing method — not a provider trait, and not a registry flag.** `no_log_prob_support()` branches only on `str`, `OpenAIModel` and `AzureOpenAIModel`; for anything else it returns `False`, and `supports_log_probs` is **never read**. The fallback happens one step later: **any `DeepEvalBaseLLM` subclass that does not define `a_generate_raw_response`** raises a plain `AttributeError` from a missing attribute, caught by the same handler the guard would have triggered. It is therefore **unconditional and automatic for every custom judge, whoever serves it** — flipping a registry flag would change nothing. Verified by execution (`docs/api-notes.md`, V3.5).
- **Changing provider does not lift that ceiling, and the reason is on our side of the wire.** The clause above is the whole argument: the fallback fires because *this repo's judge is hand-written and defines no `a_generate_raw_response`*, and that is true whoever serves it. No provider fact is needed to reach the conclusion, which is why the conclusion has outlived three providers. **The provider-side evidence is weaker than it was, and that changes nothing.** Groq's SDK volunteered a negative — its own bundled docstring said no served model honours `logprobs` (`docs/api-notes.md`, V5.3). NIM says nothing either way: `logprobs` is a recognised name on the completions endpoint's own argument allowlist, and neither the package nor NVIDIA's published reference states whether any served model honours it (V8.4, not confirmed against a live call). **Unknown is not the same as supported, and neither would lift a ceiling whose cause is a missing method in our own class.**
- **The fallback argument is specific to GEval.** Ragas' LLM metrics are prompt-and-parse and do track judge capability. Every threshold in `evals/thresholds.yaml` is therefore calibrated against the judge named by `JUDGE_MODEL` at calibration time, and is invalid the moment that value changes — a judge change is a recalibration, not a swap.

**Enforced by.** A test asserting zero network calls and $0.00 spend on a clean offline run.

**Forbidden.** In-memory-only caches. A cache in `.gitignore`. Silent fall-through to a live call on a miss. Fuzzy or normalized-away key components. Fixtures that regenerate the cache as a side effect.

### III.a — No outbound calls means none

The zero-cost guarantee is a guarantee about **packets**, not about judge calls. DeepEval emits PostHog telemetry on a path entirely independent of judging: with the judge stubbed and every metric served from cache, the process still attempts an upload.

- `DEEPEVAL_TELEMETRY_OPT_OUT=YES` is mandatory, and **must be set before `deepeval` is imported.** It therefore lives in the `env` block of `[tool.pytest.ini_options]` in `pyproject.toml`, and in the CI job environment. A `conftest.py` assignment is **forbidden** — conftest may execute after the import that reads the variable, which yields a setting that looks correct and does nothing.
- That block requires the `pytest-env` plugin (Article IX). Without it the key is silently ignored, so a test asserts the variable is actually set at collection time. **We verify the mechanism, not just the intent.**
- The guarantee is enforced by a `no_network` fixture that patches `socket.connect` to raise. **That fixture is the proof.** Grepping logs for upload errors is not proof — it detects only failures loud enough to print, and a successful exfiltration prints nothing at all.
- A blocked call must fail the test that made it. Swallowing the exception to keep the suite green inverts the entire point of Article VI.

---

## Article IV — Failure Must Be Demonstrable

**Rule.** The repo ships two app variants that are indistinguishable by inspection and unambiguously separable by measurement.

- `app/v1_naive` and `app/v2_fixed` share one interface, one corpus, and one generation model — the one named by `GENERATOR_MODEL` (Article III), **the same value for both variants**. A variant-specific generator would be a fourth axis, and the table below is exhaustive. They differ on **exactly three deliberate, named axes**, and on nothing else:

| Axis | v1_naive | v2_fixed |
|---|---|---|
| **Retrieval quality** | 200-char chunks, no overlap, `top_k=2`, no reranking | 800-char chunks with 200-char overlap, `top_k=5`, reranked |
| **Prompt discipline** | permits outside knowledge, requires no citations | forbids outside knowledge, requires citations |
| **Tool discipline** | 2–3 spurious extra calls on multi-hop cases | calls only what it needs |

- **The axes must not correlate.** Spurious tool calls are injected by a rule keyed on question *category*, never on retrieval outcome, and a test asserts v1's spurious-call set is identical whether retrieval succeeded or failed. Correlated failure modes would make it impossible to say which metric caught which problem — the entire reason `ToolCorrectness` is shown separately (II.a).
- **Every separating metric is attributed to exactly one axis**, in a table committed at `docs/attribution.md` and asserted by a test against the metrics the separation contract actually uses:

| Metric | Axis | Role |
|---|---|---|
| `faithfulness` | retrieval | separating gate |
| `context_recall` | retrieval | separating gate |
| `RefusalCorrectness` | prompt | separating gate |
| `ToolCorrectness` | tool | demonstrative only (II.a) |

- **Attribution here is asserted by construction, not proven by experiment**, and `docs/attribution.md` says so in its own text. Proving it requires the full 2×2 — retrieval × prompt, four variants, four cache sets, roughly double the screen time. That is a deliberate simplification for a ten-minute budget, recorded here so a later maintainer knows it was a choice and not an oversight. Anyone who adds the 2×2 replaces this paragraph with the measurement.
- **The illusion is a tested property, not a claim.** A vibes gate asserts that both variants produce fluent, on-topic, confident-sounding answers. If v1 starts *looking* broken, the demo has lost its point and the gate fails.
- **The separation contract:** at least three metrics must separate v1 from v2 with margin, and a test asserts it. If the demo stops demonstrating, CI goes red.
- **v1 is never fixed.** A PR that improves v1's retrieval, prompt or tool discipline is rejected on sight. Its flaws are the subject of the tutorial, not bugs in the backlog.

**Enforced by.** `test_separation_contract` — fails if fewer than three metrics clear the margin — plus a test asserting `docs/attribution.md` names exactly the metrics that separate, one axis each.

**Forbidden.** Thresholds tuned so v1 passes. A fourth axis, or an axis that is not named in the table above — an undocumented difference between the variants makes every attribution claim in this repo unfalsifiable. A v1 flaw so crude it is visible without the harness (a stack trace, an empty answer, obvious nonsense) — that proves nothing, because nobody needed an eval suite to catch it.

---

## Article V — Thresholds Are Versioned Data, Not Code

**Rule.** Every pass threshold lives in `evals/thresholds.yaml`. One file. No exceptions.

- Each entry carries its `value`, a `justification`, and the observed v1 and v2 scores that bracket it. A threshold you cannot justify in one line is a threshold you guessed.
- A missing key is a loud error, never a default. No `getattr(..., default)`, no `or 0.7`, no environment-variable override.
- A schema test asserts the file and the code agree exactly: no threshold without a metric, no metric without a threshold.
- Loosening a threshold requires the commit message to say why. This file exists so that "we made CI green" and "we made the system better" cannot be confused for one another.

**Forbidden.** Inline numeric literals in assertions. Per-environment threshold files. Thresholds in `pyproject.toml`, `conftest.py`, or a Python constants module.

---

## Article VI — No Network in CI by Default

**Rule.** The default run is offline, and offline is enforced at the socket layer — not by convention.

- A session-scoped fixture blocks outbound sockets for the entire default run. A forgotten live call fails loudly instead of silently costing money.
- Live scoring is opt-in: `-m live` plus `EVAL_LIVE=1`, in a separate, manually dispatched workflow that holds the API key secret.
- **The default CI job has no API key in its environment at all.** Not an empty one — absent.
- Refreshing the judge cache is a pull request with a visible diff, produced by the live workflow. It is never an implicit side effect of a normal run.

**Enforced by.** The socket guard itself, plus a required offline CI job on every PR. The live job is non-blocking and never gates a merge.

**Forbidden.** Network access in the default suite for any reason, including "just downloading the embedding model." Anything a viewer needs is vendored or committed.

**That ban is scoped to the default suite, and always was.** Calibration is a different actor, a different command, and a different environment: the author's machine, running `evals/cli.py`, never `uv run pytest`. A one-time model download there is **outside this rule's scope, not an exception to it** — and the half of the sentence above that faces the viewer is untouched and still literally true: *anything a viewer needs is vendored or committed.* A viewer needs the committed cache entries. A viewer never needs the model. If that ever stops being true — if a default-suite path acquires a download for any reason — this clause has been violated, not reinterpreted.

### VI.a — No implicit providers

A metric that never calls a model can still demand a provider. DeepEval metric constructors call `initialize_model(None)` eagerly, which builds an `OpenAIModel` and raises `DeepEvalError: OpenAI API key is not configured` — at construction time, before any scoring, even for metrics whose model is never used. `ToolCorrectnessMetric()` is fully deterministic and still cannot be instantiated without `OPENAI_API_KEY`.

- **Every DeepEval metric in this repo is constructed through a single factory in `evals/judge/`, which always passes an explicit `model=`.** A real judge in live mode; an offline stub judge — whose `generate`/`a_generate` raise — for deterministic metrics.
- **Constructing a DeepEval metric anywhere else is a violation**, including in a test, a fixture, or a docstring example. There is one door.
- The offline suite **asserts `OPENAI_API_KEY` is absent from the environment** and passes anyway. Not skipped, not tolerated — absent, and green. **That assertion guards the hazard named at the top of this article — DeepEval's `initialize_model(None)` — and has nothing to do with embeddings.** Since the ninth amendment it holds on *every* path rather than only the offline suite, which makes it stronger, not vestigial.
- The stub judge raising on invocation is deliberate: it converts "this metric quietly started calling a model" from a billing surprise into a test failure.

**The NIM client's construction is eager, and that keeps this rule's teeth.** The judge and the generator reach NVIDIA NIM through `openai.OpenAI(base_url=..., api_key=...)`, which resolves the credential inside `__init__` and raises `OpenAIError: Missing credentials` immediately when none is present (`docs/api-notes.md`, Verification round 8 / §V8.2). That is the same shape Groq had and the opposite of `anthropic.Anthropic()`, which deferred until first use — so the strengthened rule the eighth amendment introduced carries over intact rather than needing a new justification.

**Both NIM access paths were verified; this repository uses the OpenAI-SDK one, deliberately.** The alternative, `ChatNVIDIA` from `langchain-nvidia-ai-endpoints`, is NVIDIA's own LangChain package and was rejected on three counts (§V8.1, §V8.2, §V8.7): it needs a new dependency where the OpenAI SDK needs none, its construction is **lazy** — a missing key is only a `UserWarning`, which would quietly remove this rule's enforcement — and that warning says in its own words that it "will become an error in the future," which is a landmine rather than a guarantee. **A provider client that fails loudly on a keyless machine is worth more here than a vendor-canonical one that does not.**

- **No offline or test code path may construct a real NIM client. Not "constructed but unused" — never constructed at all.** The factory defers real-client construction until the live branch is actually entered. Every offline path uses a stub that never reaches the real constructor.
- This is deliberately **a stronger guarantee than a lazy-check assumption would permit**, and it is stronger in the direction this repo already argues for. Under a lazy client a stray constructor call is harmless, and therefore invisible — the kind of latent dependency that surfaces only when something else changes. Under an eager one the same call is a hard failure on any machine without a key, **including a viewer's, on the cold clone Article 0 promises.**
- A constructor call reached only on a branch nobody takes offline is still a violation. The rule is about what the code *can* do on the offline path, not what a particular run happened to execute.

**`base_url` is load-bearing, and this is the one place the OpenAI SDK is dangerous.** Pointed at NIM it is our client; left to its own default it is a different vendor's. **If `base_url` is ever omitted while `OPENAI_API_KEY` happens to be set, the call silently succeeds against `api.openai.com`** — different weights, a different bill, and an answer filed in the cache under a key that claims it came from NIM. Nothing in `model_identity` records the endpoint, so the store would be quietly wrong rather than loudly broken, which is the exact failure this document exists to prevent.

- **`base_url` is a single named constant at the one client-construction point, never an environment variable and never left to the SDK default.** Not configurable: Article X forbids a provider registry, and a configurable endpoint is one.
- **That is why VI.a's `OPENAI_API_KEY`-absent assertion now guards two hazards, not one** — DeepEval's `initialize_model(None)`, as before, and this silent fallback. The assertion did not change; the number of things it catches did.

**`NVIDIA_API_KEY` is the only credential this repository requires, on any path.** Calibration needs no API key at all. What it needs is a one-time local model download — `all-MiniLM-L6-v2`, ~91MB — cached under `~/.cache/huggingface`, outside the repository tree, verified unable to be swept into a commit (`docs/api-notes.md`, §V7.5).

**The same rule extends to the embeddings provider, and here it binds harder than a missing credential.** `sentence-transformers` is **absent from a viewer's environment entirely** (Article IX), so a stray construction on the offline path is an `ImportError` on a cold clone, not a credential error. The judge-client rule and this one are one rule seen from two sides: **the offline path never touches a real provider, whether that provider is unkeyed or uninstalled.** Offline embeddings use a stub, exactly as offline judging does.

**DeepEval ships no class for our provider, and that has been true of every provider this repo has used.** There is no NIM or NVIDIA model class anywhere in `deepeval==4.2.0` — the only "nvidia" strings in the installed package are `nvidia-smi` GPU diagnostics in `utils.py`, unrelated to the API (`docs/api-notes.md`, §V8.5). So the judge stays hand-written against `DeepEvalBaseLLM`, exactly as it was under Groq, which is *why* Article III's coarse-scoring ceiling is a property of our own class rather than of any vendor.

*(Dated caution, kept from the Groq era: `deepeval` ships `deepeval/models/llms/grok_model.py`, which is xAI's **Grok**, not **Groq** — there was never a `GroqModel` either (§V5.4). One transposed letter imports a different vendor's client cleanly. No longer live guidance, since this repo now uses neither; retained because the near-miss is the point.)*

**Forbidden.** A bare `SomeMetric()` call outside `evals/judge/`. Setting `OPENAI_API_KEY` or `NVIDIA_API_KEY` to a dummy value to get past construction — that trades a loud failure for a silent provider dependency, which is the thing this article exists to prevent. Constructing the NIM client without an explicit `base_url`.

---

## Article VII — Screen-Readable

**Rule.** This code will be read at 1080p by someone who has never seen it, while someone else talks over it.

- **≤ 60 lines per module. ≤ 100 characters per line.** Both machine-enforced.
- Full type hints. `mypy --strict` clean. No bare `Any` without an adjacent one-line justification.
- Every module opens with a one-line docstring stating what a viewer sees when it runs.
- Names are explanations: `context_precision`, never `ctx_prec`. No single-letter variables outside comprehension indices.
- **Boring and explicit beats DRY.** Duplication is permitted and often preferred; the cost of indirection is paid by every viewer, the cost of duplication by one maintainer. Rule of three — and even then, only if the abstraction fits on one screen.

**Forbidden.** Metaclasses. `__getattr__` interception. Decorators that generate tests. Dynamic imports. Monkeypatching outside `conftest.py`. Fixtures more than one level deep. Nested comprehensions. Any construct requiring the narrator to say "don't worry about how this works."

---

## Article VIII — Cost Transparency

**Rule.** Every run ends with a per-metric cost table, printed by default with no flag.

```
metric              calls  cached  tok_in   tok_out   USD
faithfulness           24      24   41,203     3,110   $0.00
```

- Columns: metric, calls, cache hits, input tokens, output tokens, USD. Plus a run total.
- Offline runs print the same table showing 100% cache hits and `$0.00` — the determinism budget is *demonstrated* every run, not merely asserted once.
- Prices live in a dated data file, pinned with the date they were checked and labeled as estimates. Prices change; a stale hardcoded number in Python is worse than no number. DeepEval's own registry is not that file — it lists Sonnet 5 at $3/$15 against a true $2/$10. That example is retained as dated evidence for *why* an unverified price is worse than a blank one, and it is why the rule below reads the way it does.
- A run that would exceed a configured USD ceiling aborts before spending, not after.
- **No dated NIM price table exists as of this amendment, and "free" is not one.** `build.nvidia.com` advertised "Free inference with leading models" when fetched on 2026-09-09, with no published rate, credit allowance, expiry, or limit anywhere on it or in NVIDIA's hosted API reference; `langchain-nvidia-ai-endpoints` ships a price map that is literally `{}`, and its own docstring points a caller at a *competitor's* pricing page as the convention to follow (`docs/api-notes.md`, §V8.6). **An unquantified marketing claim is not a $0.00 verified against a primary source, and this article does not treat the two as interchangeable** — a figure nobody can cite is exactly what the `UNVERIFIED` column exists to display. (The same conclusion, on the same evidence shape, as the Groq era it replaces: §V5.5–V5.6.) Until a dated, sourced table is added to `evals/pricing.yaml`, **the USD column for a call that actually happened reads `UNVERIFIED`** — never a figure computed from a third-party estimate, and never `$0.00` inferred from the word "free".
- **Token counts are exact and print unconditionally regardless.** A missing price does not excuse a missing measurement; the columns this article exists for are the ones nobody has to trust a vendor for.
- **A cached row still reads `$0.00`.** That is a fact about a call that did not happen, not a price lookup, and it needs no price table to be true. Article 0's `$0.00` demonstration and Article III's determinism budget are unaffected by the rule above.
- Fabricating a number here would violate the principle this article already states. A blank the reader can see is honest; a plausible number nobody can source is the failure this repository was built to expose, arriving in the cost table.

**Enforced by.** A pytest terminal-summary hook, so the table appears unconditionally at the end of every invocation.

---

## Article IX — Stack

Python **3.12** exactly, pinned in `.python-version`. **uv** for everything — `uv.lock` is committed, and no document in this repo ever mentions `pip`, `poetry`, `conda`, or `venv` activation. **ruff** for lint and format (`line-length = 100`). **mypy --strict**, no per-module opt-outs. Three commands total: `uv sync`, `uv run pytest`, `uv run ruff check . && uv run mypy .`.

All dependency versions are **exact pins**. No ranges, anywhere.

**A package this repository imports directly is pinned explicitly, never relied on transitively.** Getting a package "for free" because a dependency happens to pull it in is not a decision this repo made — it is another project's decision, and it can change or vanish in that project's next minor release with nothing here to notice. The tenth amendment is the live case: `openai` arrives today via `langchain-openai`, and the moment a NIM client imports it directly it becomes ours to pin. Note also what this rule does *not* license: `uv add <package>` with no version writes a **range** (`>=`), not a pin (`docs/api-notes.md`, §V8.1), so the version is spelled out or the pin is not a pin.

`pytest-env` is a required dev dependency. Article III.a's telemetry opt-out is configured through the `env` block of `[tool.pytest.ini_options]`, and `env` is not a pytest core ini key — without the plugin the block is silently ignored and the guarantee evaporates without a single error message.

**`sentence-transformers`, and the `torch`/`transformers` tree behind it, live in a dependency group `uv sync` does not install by default — never in `[project.dependencies]`.** Measured before adopting it: a 121MB download, roughly 650MB installed, close to doubling `.venv` (`docs/api-notes.md`, §V7.1). Article 0's cold clone must not pay that to install a provider the viewer's offline path never constructs.

**The `dev` group does not satisfy this requirement.** `uv sync` installs `dev` by default — `--no-dev` exists precisely as the opt-out — so a `dev` entry would land on every viewer's machine and break the Prime Contract while looking like it respected it. The group is named `calibration`, and it is absent from `[tool.uv] default-groups`. Exact pins still apply: a group outside the default install is still versioned evidence, not a shrug.

**Enforced by.** A test asserting neither package appears in `[project.dependencies]`, and that `calibration` is not among `default-groups`.

### IX.a — Pin workarounds carry dated evidence

A pin that exists to dodge an upstream bug is a claim about the world, and claims rot. Every such pin carries a comment naming **the date tested, the exact versions tested, and the exact failure** — never "pinned for compatibility."

The current instance:

> `langchain-community` is pinned to **0.4.1** because **0.4.2** regressed `ragas` 0.4.3's
> unconditional top-level import of `langchain_community.chat_models.vertexai`, which raises
> `ModuleNotFoundError` on `import ragas`. Verified 2026-09-03 by bisection over every release
> at or above 0.3.31: **0.3.31 works, 0.4.1 works, 0.4.2 fails.** 0.4.1 is the highest working
> version as of the pin date.

This is an **upstream regression and may be fixed in a later release.** The pin is therefore provisional: revisit it on any `ragas` or `langchain-community` bump, re-run the bisection, and raise the pin the moment a higher version imports cleanly. Note also that `langchain-community` is being sunset upstream, so the durable fix is likely a `ragas` release that drops the import entirely — not a newer `langchain-community`.

A pin without this evidence is indistinguishable from superstition, and gets deleted by the next person who tries.

---

## Article X — Out of Scope

Deliberately absent, and to stay absent: web UIs and dashboards; observability platforms (Langfuse, W&B, Braintrust); multi-provider abstraction layers; async anywhere; a vector database service — the store is embedded and local; a second dataset; a plugin system; anything whose value cannot be shown on screen inside ten minutes.

**Selecting a model by environment variable is not a provider abstraction layer.** Article III's `JUDGE_MODEL` and `GENERATOR_MODEL` name a model *within one provider*; they do not dispatch across providers. A provider switch, a registry of clients, a `provider=` parameter, or a second client class chosen at runtime remains out of scope, and the ban above still reaches all of them.

---

## Article XI — Trust Nothing, Including the Harness

**Rule.** The harness is under test too. A metric that has never been shown to fail is not evidence — it is decoration.

**The bug this article exists for.** `assert_test` defaults to `run_async=True`. That path routes through `deepeval.metrics.utils.copy_metrics()`, which rebuilds every metric as `type(metric)(**valid_args)`, where `valid_args` is `vars(metric)` intersected with the constructor parameter names collected across the MRO. **Any constructor argument not stored under an identically-named attribute is silently dropped and replaced by the class default.** Observed on the pinned version: a metric constructed with `score=0.1` against `threshold=0.5` was rebuilt carrying its default `0.9`, the assertion never fired, and pytest reported a pass. A red test became a green one with no error, no warning, and no log line.

This is score laundering. It is the precise failure this repository was built to expose, occurring inside the instrument built to expose it.

Three requirements, none optional:

1. **`conftest.py` forces `run_async=False` for every `assert_test` call, in exactly one place.** A single wrapper, carrying a comment that names the mechanism — `copy_metrics()` rebuilding via `type(metric)(**valid_args)` — so the next reader knows what is being defended against and can judge whether it still applies. Calling `assert_test` with the library default anywhere else is a violation.

2. **`tests/test_harness_integrity.py` reproduces the bug against the pinned `deepeval` and asserts it is STILL PRESENT.** This test is inverted on purpose: it passes while the bug exists. **If it fails, upstream has fixed it** — at which point delete the conftest workaround, delete the test, and record the fixing version in the amendment history below. A workaround with no expiry condition becomes folklore; this test is the expiry condition.

3. **Every custom metric ships with a paired negative test.** For `RefusalCorrectness` and every G-Eval metric added later, there is a test feeding it input designed to fail it, asserting that it fails. **No metric is trusted until it has been shown capable of failing.** A metric with only passing tests is indistinguishable from a metric that returns a constant, and the difference between those two is the entire subject of this repository.

**Enforced by.** `tests/test_harness_integrity.py`, plus a test asserting every metric constructed in `evals/judge/` has a corresponding negative test.

**Forbidden.** `assert_test` with the default `run_async` outside `conftest.py`. A custom metric merged without its negative test. Storing a constructor argument under a renamed or private attribute — `self._threshold` for a `threshold=` parameter — which is precisely what makes the rebuild lossy. "It passed" offered as evidence that a gate works.

---

## Amendment

These articles change only by a pull request that edits this file, states which article changes, and states what it costs. Code that violates an article is rejected — the article is not "aspirational," and "it works" is not a defense.

**Definition of done, for any change:**

1. `uv run pytest` is green offline, from a clean clone, with no API key.
2. The cost table shows `$0.00` and a full cache hit rate.
3. The separation contract still separates v1 from v2 on ≥ 3 metrics.
4. `ruff check` and `mypy --strict` are clean.
5. No module exceeds 60 lines.
6. A viewer could read the diff on screen and follow it.
7. Every metric has a negative test proving it can fail, and `tests/test_harness_integrity.py` still passes.

**Amendment history.**

- **2026-09-03 — Second amendment.** Added II.a (`ToolCorrectnessMetric` is demonstrative, not a gate), III.a (no outbound calls means none), VI.a (no implicit providers), and IX.a (pin workarounds carry dated evidence); pinned `pytest-env`. All four originate in measured behaviour recorded in `docs/api-notes.md`.
- **2026-09-03 — Third amendment.** Judge pin moved from `claude-opus-5` to `claude-sonnet-5`: all Claude tiers report `supports_log_probs=False`, so GEval degrades identically on each and the higher tier bought nothing but price. Added **Article XI — Trust Nothing, Including the Harness**, covering the `copy_metrics()` / `run_async=True` score-laundering bug, and inserted XI into Article 0's precedence chain. Added DoD item 7. *(The stated mechanism was wrong; the pin it justified was not. Corrected by the fourth amendment — this entry is left standing as the record of what was believed at the time.)*
- **2026-09-04 — Fourth amendment.** Three changes, none of them cosmetic.

  **1. Article IV — three axes, not one.** Article IV claimed "retrieval is the only difference." The app differs on retrieval, prompt *and* tool discipline, and the success criterion depends on it: `RefusalCorrectness` separates the variants because of the **prompt**. Left unamended, the constitution would have been false on its most load-bearing claim while the code was correct. Adds the named-axis table, the non-correlation requirement, and `docs/attribution.md` mapping each separating metric to one axis. **Cost:** a committed table and a test that keeps it honest; plus a written admission that with two variants attribution is asserted, not proven — the 2×2 that would prove it costs double the screen time Article 0 allows.

  **2. Article I.a — exactly one operator CLI.** Article I banned `argparse`/`click` outside `app/`. `calibrate`, `record`, `compare` and `report` produce and diff data rather than asserting on it, and forcing them through pytest would make a pytest node rewrite the thresholds every other node asserts against. Permits exactly one module, `evals/cli.py`, carved out **by name, not by pattern**, never imported by the suite and never run in default CI. **Cost:** one entry point in the repo that is not `pytest`. Article I's headline promise — the only command a viewer must learn — is unchanged.

  **3. Article III — corrected mechanism for GEval's coarse scoring.** The third amendment attributed the fallback to `supports_log_probs=False` in DeepEval's registry. Execution against the pinned version proves that flag is **never consulted** for Anthropic or custom judges: `no_log_prob_support()` branches only on `str`, `OpenAIModel` and `AzureOpenAIModel` and returns `False` for everything else. The real cause is a missing method — neither class defines `a_generate_raw_response`, so the call raises `AttributeError` into the same handler. The conclusion (every Claude tier scores coarsely, so a pricier judge buys nothing) survives intact and the `claude-sonnet-5` pin stands; only the reasoning was wrong. **Cost:** none to the code. Recorded because a constitution that keeps a correct conclusion resting on a disproven mechanism is exactly the failure mode this repository exists to expose — see `docs/api-notes.md`, V3.5.
- **2026-09-05 — Fifth amendment.** **Article III's cache key: `metric_name` → `call_kind`.** The key was written when only judge calls were cached. Folding generation into the same store left its first component unable to name half the store's own contents, because a generation call has no metric. `call_kind` — `generate:<variant>`, `ragas:<metric>`, `deepeval:<metric>` — covers every row and makes each entry self-describing to a reader. The alternatives were worse: a pseudo-metric name for generation would make one field mean two different things depending on the row, and splitting into two stores would contradict the single-store requirement and double the evidence surface a reviewer must check. **Cost:** none to any recorded evidence, since none has been recorded yet; had the cache already existed, this change would have invalidated all of it. Found by `/speckit-clarify`, where the specification and this article were caught disagreeing about the key's first field.
- **2026-09-05 — Sixth amendment.** Two changes.

  **1. Added II.b — one adapter directory, one framework per module.** Article II required each layer to adapt shared types "inside its own package," and its Forbidden clause barred an "adapter layer spanning both" — between them, they blocked the approved `evals/adapters/` layout twice over. II.b permits the single directory on the condition that each module imports exactly one framework plus `evals/golden/`, and states plainly that the property being protected is **no cross-framework leakage, enforced by import direction rather than by folder boundaries** — which a directory only ever approximated, since modules in separate packages can still import one another. The Forbidden clause is explicitly preserved: colocation is not spanning, and a base class or dispatcher bridging both frameworks stays banned wherever it sits. **Cost:** each adapter now sits one directory from its layer; bought in exchange for an import-graph assertion in CI replacing a convention a reviewer had to notice.

  **2. Article III — Trap 19 recorded as evidence for the key-completeness clause.** "Anything that moves the output moves the key" stood without proof. Ragas' `cacher()` computes a key that omits model identity entirely — verified byte-identical across `claude-sonnet-5` and `claude-opus-5` — so a naive `CacheInterface` would have served one judge's answers under another's pin, silently and green. Adds the measurement and the rule it forces: **ragas' key is accepted only as the `prompt_hash` component, never as the complete key.** **Cost:** none to the design, which already re-keyed; the article now carries the near-miss that justifies it rather than asserting the principle unsupported.
- **2026-09-05 — Seventh amendment.** Article III's `judge_identity` renamed to `model_identity`, throughout. The field was named when the store held only judge calls; the fifth amendment folded generation calls into the same store, leaving a field called `judge_identity` describing rows that have no judge. `model_identity` is the full pinned model ID plus every parameter capable of changing the call's output, whichever kind of call it is — the specification (`FR-029`) already used this name, and the constitution had fallen out of sync with its own downstream document. **Cost:** none — a rename with no behavioural change, applied to both `CONSTITUTION.md` and `.specify/memory/constitution.md`.
- **2026-09-08 — Eighth amendment.** All three model call sites — the ragas judge, the deepeval judge, and app generation — move to Groq, and the judge stops being a fixed Anthropic pin. Six changes. *(Groq was itself superseded by the tenth amendment, one day later. This entry is left standing as the record of what was decided and why; the reasoning it established — model selection by environment variable, and an eager client making the no-offline-construction rule enforceable — outlived the provider it was written for.)*

  **1. Article III — a pin becomes a selection.** `claude-sonnet-5` is replaced by two required environment variables, `JUDGE_MODEL` and `GENERATOR_MODEL`, each read through exactly one accessor that may not supply a default. The article's language is now provider-agnostic throughout. The collision this had to survive is Article 0: offline cache *reads* must compute `sha256(call_kind ‖ model_identity ‖ prompt_hash)`, so the offline path needs the model name, and a hard error on a missing variable would break the cold clone that outranks every article here. Resolved by committing the suite's values to the `env` block of `[tool.pytest.ini_options]` — Article III.a's existing mechanism, with III.a's existing "verify the mechanism, not just the intent" test applied to the new variables. The accessors still hard-error everywhere else, which is where the guarantee was actually needed: `evals/cli.py` and every live pass.

  **2. Article III — the judge model was declared in three places.** `evals/ragas_llm.py`, `evals/judge/cached.py` and `evals/ops/record.py` each carried their own `JUDGE_MODEL = "claude-sonnet-5"`. Three copies of a value the cache key derives from is a divergence waiting to happen, and had one drifted, the two halves of the store would have keyed the same call differently with neither copy looking wrong. The single-accessor rule collapses it.

  **3. Article VI.a — eager construction, stated as a stronger guarantee.** `groq.Groq()` raises inside `__init__` when no key is present, where `anthropic.Anthropic()` deferred (V5.2). VI.a was written under the lazy assumption, which tolerated a client constructed and never called. It no longer does: **no offline or test path may construct a real Groq client at all.** The old behaviour made a stray constructor call harmless and therefore invisible; the new one makes it a hard failure on any machine without a key — including a viewer's, on the cold clone.

  **4. Article VIII — `UNVERIFIED` instead of a fabricated figure.** No dated Groq price table exists: Groq's public pricing page carried no rates when fetched on 2026-09-08, and the SDK ships no registry (V5.5–V5.6). The USD column for a call that happened now reads `UNVERIFIED` until a sourced table lands in `pricing.yaml`. Token counts stay exact and unconditional, and a **cached** row still reads `$0.00` — a fact about a call that did not happen, not a price lookup — so Article 0's `$0.00` demonstration survives intact.

  **5. Three stale claims corrected.** GEval's coarse scoring was attributed to "Claude judges"; the real cause is **any `DeepEvalBaseLLM` subclass lacking `a_generate_raw_response`**, which is provider-neutral — and Groq does not lift the ceiling, since its SDK exposes `logprobs` parameters that no served model honours (V5.3). Article III's sampling-parameter ban was justified by Claude returning a 400; Groq accepts `temperature` as an ordinary parameter, so the rule keeps its force and gets an honest reason — **a knob the provider rejects cannot silently widen the cache's blast radius, and a knob it accepts can.** Article IV's `claude-haiku-4-5` generator pin becomes `GENERATOR_MODEL`, with the shared-model requirement made explicit, because a variant-specific generator would be a fourth axis.

  **6. Housekeeping.** `evals/judge.py` → `evals/judge/` in Articles VI.a and XI, stale since Slice 3 made it a package. Article X gains an explicit line that env-var model selection within one provider is **not** the multi-provider abstraction layer it bans, so the two cannot be read against each other later. The `grok_model.py` (xAI **Grok**) versus **Groq** name collision is recorded in VI.a as a documentation caution — `deepeval` ships the former and has no `GroqModel` at all, and one transposed letter imports a different vendor's client cleanly.

  **Cost: none to any recorded evidence, because there is none yet.** `evals/.judge_cache/` holds zero entries at the time of this amendment. Had T3.8a and T3.8b already run, this change would have invalidated every committed entry and every calibrated threshold in one commit — the same timing argument the fifth amendment made about `call_kind`, and the second time this repository has been saved by not having done the expensive thing yet. Anthropic is unpinned as a provider but **not erased**: the Trap 19 key-collision measurement, V3.5's coarse-scoring finding, and Article VIII's $3/$15-vs-$2/$10 example are kept in the provider's own names, because they are dated evidence for rules that are provider-neutral, and rewriting a measurement to match a later decision is the failure this repository exists to expose. Applied to both `CONSTITUTION.md` and `.specify/memory/constitution.md`.
- **2026-09-08 — Ninth amendment.** `ResponseRelevancy`'s embeddings move from OpenAI's `text-embedding-3-small` to a local `sentence-transformers` model (`all-MiniLM-L6-v2`, ~91MB) via `langchain_community.embeddings.HuggingFaceEmbeddings`, which the pinned stack already carries. **`GROQ_API_KEY` becomes the only credential this repository requires, on any path** — calibration now needs no API key at all, only a one-time local download cached outside the repository tree. Three changes.

  **1. Article VI — a scope clarification, not an exception.** That article's Forbidden clause bans network access in the default suite "for any reason, including *just downloading the embedding model*" — wording that reads, at first glance, as a direct prohibition on what this amendment introduces. It is not, and the distinction is in the clause's own first five words: **in the default suite.** Calibration is a different actor, command and environment — the author's machine running `evals/cli.py`, never `uv run pytest`. The sentence is left byte-unchanged and the clarification appended below it, including the condition under which this reasoning would be a violation rather than a reading: if a default-suite path ever acquires a download, the clause has been broken, not reinterpreted.

  **2. Article IX — the dependency that must never reach a viewer.** `sentence-transformers` pulls `torch` and `transformers`: measured at a 121MB download and roughly 650MB installed, close to doubling `.venv` (`docs/api-notes.md`, §V7.1). It therefore lives in a `calibration` group that `uv sync` does not install. **The `dev` group would not have worked** — `uv sync` installs `dev` by default, which `--no-dev` exists to opt out of, so a `dev` entry would have shipped 650MB to every viewer while looking like it respected Article 0. That was checked before choosing, not after.

  **3. Article VI.a — the offline-construction rule extends to embeddings.** The eighth amendment forbade constructing a real Groq client on any offline path because the credential check is eager. The same rule now covers the embeddings provider for a harder reason: the package is *absent* from a viewer's environment, so a stray offline construction is an `ImportError` on a cold clone rather than a credential error. Stated as one rule seen from two sides — the offline path never touches a real provider, unkeyed or uninstalled. VI.a's `OPENAI_API_KEY`-absent assertion is deliberately **kept**: it guards DeepEval's `initialize_model(None)` implicit-provider hazard, which was never about embeddings, and it now holds on every path rather than only the offline suite.

  **For the record, not as a rule.** `HuggingFaceEmbeddings` defines only the synchronous `embed_query`/`embed_documents`; its `aembed_*` methods come from `langchain_core`'s base class as `run_in_executor(None, self.embed_query, …)` — real `async def` methods, sync-in-a-thread underneath, not genuine async I/O (`docs/api-notes.md`, §V7.4). Harmless *here* only because Article XI already forces synchronous execution throughout. This is a fact about this repository's usage, not a general guarantee about the wrapper, and it should be re-checked by anyone who ever relaxes Article XI.

  **Cost: none to any recorded evidence, because there is still none.** `evals/.judge_cache/` holds zero entries — the third consecutive amendment saved by that timing, and the last one that will be, since the next live pass ends it. The standing trade is ~650MB in the author's calibration environment against zero credentials and zero recurring cost on the viewer's path. What is spent instead is Article IX's simplicity: this repository now has a dependency group a reader must know not to install, which is one more thing to explain than "run `uv sync`." Accepted because the alternative was keeping a second provider's API key alive for a single metric's embeddings. Applied to both `CONSTITUTION.md` and `.specify/memory/constitution.md`.
- **2026-09-09 — Tenth amendment.** All three model call sites move from Groq to **NVIDIA NIM**, reached through `openai.OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=...)`. **`NVIDIA_API_KEY` replaces `GROQ_API_KEY` as the only credential this repository requires, on any path.** `JUDGE_MODEL` and `GENERATOR_MODEL` are unchanged as mechanisms and now hold NIM model identifiers. Five changes.

  **1. Article VI.a — the client, and why this one.** NIM is reachable two ways and both were verified (`docs/api-notes.md`, Verification round 8). The OpenAI SDK against a NIM `base_url` was chosen over NVIDIA's own `ChatNVIDIA` on three counts: it adds **no new dependency** — `openai` is already present, so the net change is one pin promoted and `groq` dropped (§V8.7) — its construction is **eager**, raising `OpenAIError` with no key (§V8.2), and `ChatNVIDIA` is **lazy**, downgrading a missing key to a `UserWarning` while announcing in that same warning that it "will become an error in the future." **The eager client was preferred precisely because it fails loudly on a keyless machine**, which is what makes VI.a's no-offline-construction rule enforceable rather than aspirational. That the vendor-canonical package lost on this criterion is the point, not an accident.

  **2. Article VI.a — a new hazard, created by the choice above.** Using the OpenAI SDK against a non-OpenAI endpoint means `base_url` is the only thing distinguishing our provider from OpenAI's. Omit it while `OPENAI_API_KEY` happens to be set and the call **silently succeeds against `api.openai.com`** — different weights, a different bill, and the answer filed under a cache key that claims NIM served it. `model_identity` does not record the endpoint, so the store would be quietly wrong rather than loudly broken. `base_url` is therefore a single named constant, never an environment variable (Article X forbids a provider registry) and never left to the SDK default. **VI.a's `OPENAI_API_KEY`-absent assertion did not change; the number of hazards it catches went from one to two.**

  **3. Article III — two rationales re-sourced, no rule touched.** The sampling-parameter ban and the coarse-scoring ceiling both kept their text and lost a provider-specific support. Temperature: Claude rejected it, Groq accepted it, and **round 8 never tested NIM**, so the article now says so rather than inferring acceptance from an OpenAI-shaped schema. Logprobs: Groq's SDK volunteered that no model honours them; NIM is **silent** — a recognised argument name with no statement either way (§V8.4). Rather than resting the ceiling on a weaker provider fact, it now rests where V3.5 proved it belongs — **on our own hand-written judge having no `a_generate_raw_response`**, which is true whoever serves it. The conclusion has outlived three providers because it never depended on one.

  **4. Article VIII — the same `UNVERIFIED` verdict, reached differently.** Groq had no published rates; NVIDIA has something slightly worse — a *claim* of "Free inference with leading models" with no rate, credit, expiry or limit behind it, and a shipped price map that is literally `{}` whose docstring points at a competitor's pricing page (§V8.6). **"Free" is not $0.00 verified against a primary source**, and this amendment writes that distinction down rather than letting a marketing word become a number in a cost table.

  **5. Article IX — direct imports are pinned explicitly.** Earned by this change: `openai` currently arrives transitively through `langchain-openai`, and a client that imports it directly cannot keep depending on another project's dependency choices. The clause also records that `uv add` with no version writes a range, not a pin (§V8.1) — the exact way this rule gets broken by accident.

  **Cost: this is the first amendment that is not free, and the ninth predicted it.** That entry closed by calling itself "the last one saved by that timing, since the next live pass ends it." The pass ran on 2026-09-09. `evals/.judge_cache/` held **191 entries**, and changing `JUDGE_MODEL`/`GENERATOR_MODEL` **invalidates 149 of them** — every `generate:*` and every `ragas:*` metric key, since both derive from the two values this amendment changes. **42 `ragas:embeddings` entries survive**, keyed on the local `sentence-transformers` model the ninth amendment moved in-process — an unplanned dividend of that decision, and the first time this repository's evidence has partially survived a provider change. No `deepeval:*` entries existed to lose; T3.8a has never run. **The invalidated evidence was committed first, at `4584441`, specifically so this amendment orphans it in the open** — Article III requires a cache change to be reviewable as a change to the evidence, and that applies most when the change is deletion by another name. Nothing was discarded and nothing was rewritten to match the new decision.

  **Flagged, and deliberately not adopted: a path that might lift Article III's coarse-scoring ceiling.** §V8.5 found that `deepeval`'s own `LiteLLMModel` **does** define `a_generate_raw_response` — the method whose absence causes the fallback — unlike every provider judge this repository has hand-written across three providers. It is the first candidate for fine-grained GEval scoring that has appeared in four rounds of investigation. It is **not** adopted here: `litellm` was never installed, no live call was made, and neither its cache hook nor its cost-table source was inspected — the checks `AnthropicModel` and the Groq judge each had to pass. Recorded so a future amendment starts from a known lead rather than rediscovering it. Applied to both `CONSTITUTION.md` and `.specify/memory/constitution.md`.

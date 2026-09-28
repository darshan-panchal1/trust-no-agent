# Feature Specification: Per-Record Evaluator Contract

**Feature Branch**: n/a (no branch hook is configured; the spec was written on `main`)

**Created**: 2026-09-26

**Status**: Implemented (2026-09-28)

**Target release**: v1.1.0 (additive; no existing surface changes)

**Input**: User description: "Add a stable, additive per-record evaluator contract alongside the existing EvalSuite/RunSummary API, so a caller can score its own (input, output, expected, contexts) records against any trustnoagent metric, one record at a time, without importing Ragas or DeepEval directly." The full constraint list, stories and acceptance criteria are in the `/speckit-specify` invocation of 2026-09-26. Reference: `docs/research/brief.md` §8, "Proposed integration contract".

## Context

Today the only public way to score anything is `EvalSuite.run()`. It runs the repo's own golden dataset through the two built-in agents (`v1_naive` and `v2_fixed`) and returns averages per metric. A caller with their own agent cannot ask a narrower question: "how does this one answer score on faithfulness?" To get that answer they have to import Ragas or DeepEval, rebuild the NIM-routed judge, and bypass the committed evidence cache. That reintroduces every trap this repo exists to catch.

This feature adds a second, narrower door with these properties:
- It scores **one caller-supplied record at a time** with **one named evaluator**.
- It returns **one result** that explains itself: a status, a score or label, the judge that produced it, and a fingerprint of how it was judged.
- It never raises, never returns a silent 0, and never quietly drops a failed result.

Everything the v1.0.0 surface does today stays byte-identical.

## Clarifications

### Session 2026-09-26

- **Q: Article II forbids one entry point routing to both frameworks. Amend it, or restructure?**
  → Amend. The Eleventh amendment adds Article II.c, which permits exactly one routing facade, named by path: a single entry point with no shared base class. Framework-neutral contract modules may be imported by both sides. Each framework adapter still imports only its own framework.
- **Q: What is `tna.deepeval.answer_relevancy`?**
  → Not shipped. v1.1.0 ships every metric v1 already scores and holds evidence for, plus caller-defined rubric judges under `tna.judge.<name>`. *(Corrected 2026-09-26: the first answer shipped only `response_relevancy` and `refusal_correctness`. That left out `faithfulness` and `context_recall`, two of the three metrics `EvalSuite.gate()` gates on, which defeats the point of a regression-gating contract. All five now ship.)*
- **Q: Where are live results for caller records cached?**
  → In a caller-supplied cache directory, given as a parameter and never as an env var. It defaults to the committed `evals/.judge_cache/` only inside a repo checkout. Outside one, the caller must pass a directory, and omitting it returns an `error` result.
- **Q (planning, 2026-09-26): Where does offline/live mode live?**
  → On the judge configuration (`JudgeConfig.from_env(mode=...)`). This keeps the evaluator contract's `evaluate(record, judge)` signature exactly as specified.

## User Scenarios & Testing *(mandatory)*

### User Story 1: Score one record with one named evaluator (Priority: P1)

A developer has an answer from their own agent: the question, the answer, the retrieved passages, and a reference answer. They call one entry point with an evaluator id such as `tna.ragas.response_relevancy` and the record. They get back one result: a status, a score, the judge model that produced it, and a fingerprint. They never import Ragas or DeepEval.

**Why this priority**: This is the whole feature. Every other story extends or describes this path. Without it the contract has nothing to carry.

**Independent Test**: Take a record whose judge responses are already in the committed evidence store. Score it offline with each built-in evaluator. Each call returns status `ok` and a numeric score equal to what the existing path computes for the same inputs, with no network access and $0.00 spent.

**Acceptance Scenarios**:

1. **Given** a record with input and output, and a committed cache entry for it, **When** the caller scores it offline with `tna.ragas.response_relevancy`, **Then** the result has status `ok`, a score in [0, 1], the judge model, and a fingerprint, and no network call is attempted.
2. **Given** the same record scored twice with the same evaluator and the same fingerprint, **When** both results are compared, **Then** they are identical in every field except the measured latency, and the second call is served from the evidence store under the existing cache key format.
3. **Given** a record from an agent that is neither `v1_naive` nor `v2_fixed`, **When** it is scored live with valid credentials, **Then** the result is produced exactly as for a built-in agent's record. Nothing on this path depends on which agent produced the output.
4. **Given** the caller imports only this package's public API, **When** they score a record, **Then** they write no import of Ragas, DeepEval or the NIM client.

---

### User Story 2: Discover what evaluators exist (Priority: P1)

A developer, or a downstream tool such as the platform in the research brief, lists every evaluator this package offers. Each entry shows a stable id, a version, the record fields it needs, and its output type. From that listing alone they can choose evaluators and check a record before scoring it.

**Why this priority**: Without a listing, ids are guesswork, and a downstream tool cannot check a record against an evaluator's needs before spending money.

**Independent Test**: List the evaluators. Every built-in evaluator appears exactly once, with a namespaced id, a version that names the upstream library version it wraps, a non-empty set of required fields, and one output type. Calling the listing needs no credentials and no network access.

**Acceptance Scenarios**:

1. **Given** a fresh install with no environment configured, **When** the caller lists evaluators, **Then** the listing returns without error and without reading `JUDGE_MODEL`, `GENERATOR_MODEL` or `NVIDIA_API_KEY`.
2. **Given** the listing, **When** any entry's id is passed to the scoring entry point, **Then** it resolves. **When** any id not in the listing is passed, **Then** the result has status `error` and names the unknown id.
3. **Given** the ids shipped in v1.1.0, **When** later minor releases ship, **Then** those ids still resolve to the same metric. An id is never reused for a different metric.

---

### User Story 3: Failures are results, not exceptions (Priority: P1)

A caller scores a batch of records in a loop. Some records lack a field the evaluator needs. A judge call times out. The judge returns malformed output. An offline run hits a record with no cached evidence. Credentials are missing for a live run. Every one of these comes back as a result with a status and a reason. The loop never crashes, and no failure turns into a number that averages in as if it were real.

**Why this priority**: The brief's first scoring rule is "never coerce failures to 0". The existing path both stops on the first error and skips NaN without telling anyone. The new path exists partly so callers get the honest version, so it ships in the first release.

**Independent Test**: Feed one record for each failure class and check each status:
- missing required field → `skipped`
- unknown evaluator → `error`
- offline cache miss → `error`
- missing credential in live mode → `error`
- unparseable or out-of-range judge output → `invalid_output`

In every case the score is empty (never 0, never NaN) and no exception escapes.

**Acceptance Scenarios**:

1. **Given** a record without contexts, **When** it is scored with an evaluator that requires contexts, **Then** the status is `skipped`, the score is empty, the reason names the missing field, and no judge call is made.
2. **Given** offline mode and a record with no cached evidence, **When** it is scored, **Then** the status is `error`. The reason names the missing cache key and says that scoring a new record needs live mode. No network call is attempted.
3. **Given** the judge returns text that fails the evaluator's output validation, **When** the result is built, **Then** the status is `invalid_output`, the score and label are empty, and the judge's raw text is kept on the result.
4. **Given** any failure status, **When** the caller reads the result, **Then** the score is empty. It is never 0.0 and never NaN.

---

### User Story 4: Custom rubric judge through the same path (Priority: P2)

A developer defines their own judge: a name, plain-language instructions, and either an allowed set of labels (for example `{"pass", "fail"}`) or a numeric score range. They score records with it through the same entry point, passing the rubric definition in place of an id, and get the same result shape, statuses and fingerprinting as the built-in evaluators. Its id is `tna.judge.<name>`. It appears in the listing when the caller passes it to the listing call. No process-wide rubric registry exists.

**Why this priority**: The brief says user-defined rubric judges should live in trustnoagent, so there is one judge client and one cache. The built-in evaluators already deliver value without this story, so it comes second.

**Independent Test**:
1. Define a label rubric and a score-range rubric.
2. Score one known-good record and one known-bad record with each. The known-bad record must produce a failing label or a low score.
3. Feed a judge response outside the allowed labels or range. It must produce `invalid_output` with the raw text kept.

**Acceptance Scenarios**:

1. **Given** a rubric with allowed labels `{"pass", "fail"}`, **When** the judge returns `"pass"`, **Then** the status is `ok`, the label is `"pass"` and the score is empty.
2. **Given** a rubric with a score range of 1–5, **When** the judge returns 7, **Then** the status is `invalid_output` and the raw text is kept.
3. **Given** two rubrics with the same name but different instructions, **When** each scores the same record, **Then** their fingerprints differ, and neither is served the other's cached answer.
4. **Given** a rubric, **When** it is defined, **Then** the rubric ships with a demonstration that it can fail on a known-bad input (Article XI: "a metric that has never been shown to fail is not evidence").

---

### User Story 5: One judge configuration object from the environment (Priority: P2)

A caller builds a single judge-configuration object from the existing environment variables instead of reading them one by one. The object carries:
- the judge model and the generator model, both required and never defaulted;
- the API key, required only when live calls will be made;
- the NIM base URL, taken from the existing hardcoded constant and never from the environment.

**Why this priority**: It removes three separate environment reads from every caller, and it is the contract shape the brief's downstream platform expects. The P1 stories can read the environment internally, so this can follow them.

**Independent Test**:
- With `JUDGE_MODEL` and `GENERATOR_MODEL` set, building the object succeeds offline without `NVIDIA_API_KEY`.
- With either model variable unset, it fails with an error naming that variable.
- Setting any environment variable named like a base URL has no effect on the URL the object reports.

**Acceptance Scenarios**:

1. **Given** `JUDGE_MODEL` is unset, **When** the object is built, **Then** it fails with the existing message that names `JUDGE_MODEL`. This is the same rule the current accessors enforce.
2. **Given** both model variables are set and `NVIDIA_API_KEY` is absent, **When** the object is built for offline use, **Then** it succeeds. **When** it is used for a live score, **Then** the result has status `error` with a reason naming `NVIDIA_API_KEY`. No bare exception is raised.
3. **Given** an environment variable such as `NIM_BASE_URL` is set to any value, **When** the object is built, **Then** its base URL is still the hardcoded constant.

---

### User Story 6: Every result carries a judging fingerprint (Priority: P2)

A caller comparing two runs needs to know whether they were judged the same way. Every result on the new path carries a fingerprint: the judge model, the evaluator's template id and version, the decoding parameters, and the output schema. It is attached as metadata on the result and stored beside the cache entry, never folded into the cache key.

**Why this priority**: The brief lists judge and template drift as an MVP-level risk, and the fingerprint is the only defence against it. Stories 1–3 work without it, so it is P2. The fields are still defined in v1.1.0, so the contract ships complete.

**Independent Test**:
- Score the same record twice with the same configuration: the fingerprints are equal.
- Change the judge model: the fingerprint changes.
- Take one of the existing committed cache entries: it still resolves under its current key, and its result reports that no fingerprint was recorded for it.

**Acceptance Scenarios**:

1. **Given** two results for the same record, evaluator and configuration, **When** their fingerprints are compared, **Then** they are equal.
2. **Given** an existing (v1.0.0-era) cache entry with no stored fingerprint, **When** the new path serves it, **Then** the result is `ok`, the entry still resolves under its unchanged key, and the result marks its fingerprint provenance as "not recorded".
3. **Given** a cache entry whose stored fingerprint differs from the fingerprint the current configuration would produce, **When** the new path would serve it, **Then** it is not served silently. The result has status `error`, names both fingerprints, and keeps the stored raw text.

---

### User Story 7: Real token counts for Ragas evaluators on the new path (Priority: P3)

A caller tracking judge cost sees real input and output token counts on results from Ragas evaluators, not the 0/0 that Ragas-backed cache entries record today. The existing path's cost recording does not change.

**Why this priority**: Cost visibility (Article VIII) matters, but a wrong count here does not produce a wrong score.

**Independent Test**: Score a record live with a Ragas evaluator. The result reports token counts greater than zero that match what the provider returned. A result served from a v1.0.0-era Ragas cache entry reports its token counts as unknown, not 0.

**Acceptance Scenarios**:

1. **Given** a live Ragas evaluation, **When** the result is returned, **Then** input and output token counts equal the provider's reported usage, summed across every judge call the metric made for that record.
2. **Given** a result served from a Ragas cache entry that recorded 0/0, **When** it is returned, **Then** its token counts are unknown (empty), not 0.
3. **Given** the existing `EvalSuite`/`record` path, **When** it runs after this feature ships, **Then** its cost table is byte-identical to v1.0.0 for the same committed evidence.

---

### Edge Cases

- **Empty string versus missing field.** A record with `contexts=[]` or `output=""` is present but empty. It is scored, not skipped. Only an absent required field produces `skipped`.
- **Evaluator that needs embeddings in live mode on a default install.** `tna.ragas.response_relevancy` needs an embeddings model that is not installed by default; it lives in the author-only calibration group (Article IX). In live mode on a default install, the result is `error` with a reason naming the missing optional install. The call does not fail at import time.
- **Offline cache miss for a caller's own record.** This is the common case. The `record` refresh command only covers the built-in dataset, so the reason must point to live mode, not to `record`.
- **Partial Ragas failure.** A multi-step Ragas metric such as Faithfulness can fail on its second judge call after its first call succeeded. The result is one failure status: `invalid_output` if a response failed to parse, `error` otherwise. Token counts cover the calls that were actually made.
- **Judge returns an empty object, or valid JSON with the wrong shape.** The status is `invalid_output`; valid JSON alone is not success.
- **Rubric name collisions.** A rubric cannot shadow a built-in evaluator: ids live in separate namespaces (`tna.judge.*` versus `tna.ragas.*` and `tna.deepeval.*`). Rubric names are limited to lowercase letters, digits and underscores, and an invalid name is refused at definition time. Two rubrics with the same name but different content are distinct: their prompts and fingerprints differ, so neither is served the other's evidence.
- **A string id in the `tna.judge.` namespace.** Rubrics are passed as definitions, not looked up by id, so a bare `"tna.judge.x"` string returns `error` explaining that rubric judges are evaluated by passing their definition.
- **Cost accounting.** Live calls on the new path land in Article VIII's per-run cost rows, the same as existing calls, because they go through the same evidence-store door. The `record` command's USD ceiling is not reachable from this path; see FR-035.
- **A cache entry the new path writes and the old path later reads.** Such an entry carries real token counts and a stored fingerprint. The old path must still read it unchanged; the extra field is ignored. Its cost table would then show those real counts for that entry, which is a truthful difference and not a change in the old path's behaviour.
- **Sampling parameters.** Callers cannot pass temperature, top_p or top_k to any evaluator or rubric (Article III bans them everywhere). The decoding parameters in the fingerprint record what was actually sent, which today is none of these.

## Requirements *(mandatory)*

### Functional Requirements

**Scoring entry point**

- **FR-001**: The package MUST expose one public, synchronous entry point. It takes:
  - an evaluator id, or a rubric definition;
  - one record;
  - an optional judge configuration, which carries the offline/live mode;
  - an optional cache directory.

  It returns exactly one result. It MUST NOT return a coroutine or require an event loop (Article X).
- **FR-002**: A record MUST carry these fields, each of which may be absent: `input`, `output`, `expected`, `contexts` (an ordered list of passages), and free-form `metadata`. The record MUST NOT require any field from the built-in golden-case schema (such as `category` or `expected_tools`).
- **FR-003**: The mode MUST default to offline. Offline MUST make no network call under any outcome. Live MUST be an explicit per-call choice. No new environment variable may enable it.
- **FR-004**: The entry point MUST NOT raise for any evaluation-time failure. Unknown ids, missing fields, cache misses, missing credentials, provider errors, timeouts and malformed judge output MUST all be returned as results. Programming errors by the caller, such as passing a non-record object, MAY raise.
- **FR-005**: Callers MUST be able to use the entry point without importing Ragas, DeepEval, `instructor` or `openai` themselves.

**Registry and listing**

- **FR-006**: The package MUST expose a listing of every registered evaluator. Each entry MUST show its id, version, required record fields, and output type (`score`, `label` or `bool`).
- **FR-007**: Evaluators MUST be registered by direct import into one registry module inside this package. There MUST be no entry-point, plugin or dynamic-discovery mechanism (Article X).
- **FR-008**: Built-in ids MUST be namespaced `tna.<framework>.<metric>`. v1.1.0 MUST register exactly the five metrics v1 already scores, each with committed evidence: `tna.ragas.faithfulness`, `tna.ragas.context_recall`, `tna.ragas.context_precision`, `tna.ragas.response_relevancy` and `tna.deepeval.refusal_correctness`. Three of them (`faithfulness`, `context_recall`, `refusal_correctness`) are the metrics v1 gates on. `tna.deepeval.answer_relevancy` is not shipped.
- **FR-009**: Rubric judges MUST carry the id `tna.judge.<name>` and MUST appear in the listing when passed to it. Ids, once released, MUST be stable across minor releases and MUST NOT be reused for a different metric.
- **FR-010**: An evaluator's version MUST identify both the evaluator's own version and the pinned upstream library it wraps (for example, `1.1.0+ragas0.4.3`, `1.1.0+deepeval4.2.0`).
- **FR-011**: `ToolCorrectness` MUST NOT be registered in v1.1.0. The record has no tool-call fields, and Article II.a keeps that metric demonstrative, never a gate.
- **FR-012**: The listing MUST be available without credentials, without model environment variables, and without network access.

**Result and statuses**

- **FR-013**: A result MUST carry:
  - the evaluator id and version;
  - a status: one of `ok`, `error`, `skipped`, `invalid_output`;
  - a score (number or empty), a label (text or empty), and an explanation (text or empty);
  - the judge model (or empty for evaluators that call no model) and the judging fingerprint, including its provenance;
  - latency in milliseconds;
  - input and output token counts (each a number or unknown);
  - an error reason (text or empty);
  - the raw upstream payload, for audit.
- **FR-014**: Status MUST be `ok` if and only if a valid score or label was produced. For every other status, score and label MUST be empty. A failure MUST never be reported as 0, and NaN MUST never appear in a result.
- **FR-015**: A record missing a field the evaluator requires MUST yield `skipped`, with a reason naming the field. No judge call may be made.
- **FR-016**: Judge output that cannot be parsed, has the wrong shape, falls outside an allowed label set, or falls outside an allowed score range MUST yield `invalid_output`, with the judge's raw text kept on the result.
- **FR-017**: An offline cache miss MUST yield `error`. The reason MUST name the missing key (Article III: a miss names the missing key) and state that new records require live mode.
- **FR-018**: A live call without `NVIDIA_API_KEY` MUST yield `error` naming that variable. It MUST NOT surface as an unhandled exception.
- **FR-019**: Where the upstream metric produces a reason, the result's explanation MUST carry it (for example, GEval's reason). Otherwise the explanation is empty.

**Rubric judges**

- **FR-020**: A caller MUST be able to define a rubric judge with a name, instructions, the record fields the instructions use, and exactly one of: an allowed label set, or a numeric score range (minimum and maximum).
- **FR-021**: Rubric judges MUST score through the same entry point, statuses, fingerprinting, caching and cost accounting as the built-in evaluators.
- **FR-022**: A rubric's template identity MUST include its instructions and its allowed labels or range. Changing any of them MUST change the fingerprint and MUST NOT serve a previous definition's cached answer.
- **FR-023**: The package MUST ship a test showing a rubric judge producing a failing label or low score on a known-bad record (Article XI).

**Judge configuration**

- **FR-024**: The package MUST provide a judge configuration object with a `from_env()` constructor. The constructor reads `JUDGE_MODEL` and `GENERATOR_MODEL` through the existing required accessors, with no defaults. It reads `NVIDIA_API_KEY` only when live use is requested.
- **FR-025**: The configuration's base URL MUST be the existing hardcoded NIM constant. `from_env()` MUST NOT read any environment variable for it.
- **FR-026**: No environment variable beyond `NVIDIA_API_KEY`, `JUDGE_MODEL` and `GENERATOR_MODEL` may be required by anything this feature adds.

**Fingerprint and cache**

- **FR-027**: Every new-path result MUST carry a fingerprint composed of: judge model, evaluator template id and version, decoding parameters actually sent, and output schema. The same inputs MUST always produce the same fingerprint.
- **FR-028**: The cache key format MUST remain `sha256(call_kind ‖ model_identity ‖ prompt_hash)`, unchanged. The fingerprint MUST be stored as a separate field beside the cache entry and MUST NOT be folded into the key.
- **FR-029**: Every one of the existing committed cache entries MUST still resolve under its current key, on both the old path and the new path. Entries without a stored fingerprint MUST be served on the new path with fingerprint provenance marked "not recorded".
- **FR-030**: If a stored fingerprint exists and differs from the one the current configuration produces, the new path MUST NOT serve that entry as `ok`. It MUST return `error`, naming both fingerprints (see User Story 6).
- **FR-031**: New-path cache entries MUST use one of the three existing `call_kind` forms (`generate:*`, `ragas:*`, `deepeval:*`) (Article III). A fourth form requires a constitutional amendment and is out of scope.
- **FR-032**: The new path MUST read and write evidence in a caller-supplied cache directory, passed as a parameter and never as an environment variable. When none is given, it MUST default to the committed `evals/.judge_cache/`, but only when running inside a repo checkout. Outside a checkout it MUST return `error` asking for a directory. The key format and file layout inside the directory MUST be unchanged.

**Token accounting**

- **FR-033**: Ragas-backed evaluations on the new path MUST report the real input and output token counts the provider returned, summed across every judge call made for that record.
- **FR-034**: A result served from a cache entry that recorded 0/0 tokens (the existing Ragas behaviour) MUST report token counts as unknown, not 0.
- **FR-035**: New-path calls MUST appear in Article VIII's cost accounting, per `call_kind`, the same as existing calls.
  - A USD ceiling is not added to this path. NIM has no dated price (Article VIII), so any ceiling would be inert, the same way `record --allow-unpriced` already is.
  - The spending controls stay where they are today: the explicit per-call live mode and the credential.

**Non-regression**

- **FR-036**: `EvalSuite`, `RunSummary`, `run_gate`, `Mode` and `__version__`'s meaning MUST keep their v1.0.0 names, signatures and behaviour. The CLI commands (`record`, `calibrate`, `compare`, `report`, `gate`) MUST produce byte-identical output and exit codes for the same inputs. The GitHub Action's behaviour MUST be unchanged.
- **FR-037**: The existing path's handling MUST be untouched: 0.0 for a missing metric in `compare`, NaN-skipping means, stop-on-first-error, and 0/0 Ragas token recording.
- **FR-038**: No dependency pin may change, loosen or be added as a range. Python stays exactly 3.12, and DeepEval stays exactly 4.2.0 (Article IX).
- **FR-039**: The default offline test suite MUST remain green on a cold clone with no API key and $0.00 spent (Article 0).
- **FR-040**: The public entry point MUST be the single routing facade that Article II.c (Eleventh amendment) names by path.
  - The facade imports no framework itself.
  - Each per-framework adapter imports only its own framework.
  - Shared types live only in framework-neutral contract modules.
  - No base class is shared between the two sides, and no score is combined across evaluators.

### Key Entities

- **Evaluation record**: One caller-supplied unit to score: input, output, expected answer, ordered contexts, and free-form metadata. Every field is optional at the type level; each evaluator declares which fields it needs.
- **Evaluator**: A named, versioned scoring procedure with a stable id, the record fields it requires, and one output type. It is either a built-in metric (Ragas or DeepEval) or a caller-defined rubric judge.
- **Evaluator listing**: The read-only catalogue of registered evaluators: id, version, required fields and output type for each.
- **Rubric judge definition**: A name, instructions, the fields the instructions use, and either an allowed label set or a score range. It is registered as `tna.judge.<name>`.
- **Evaluation result**: The single outcome of scoring one record with one evaluator: status, score or label, explanation, judge model, fingerprint and its provenance, latency, token counts (or unknown), error reason, and raw payload.
- **Judge configuration**: The judge model, the generator model, the offline/live mode, the API key (live only), and the fixed NIM base URL, built once from the three existing environment variables.
- **Judging fingerprint**: A deterministic identity of how a result was judged: judge model, template id and version, decoding parameters, and output schema. It is stored beside a cache entry, never in its key, and carries a provenance of either "recorded" or "not recorded".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer with their own agent can score one answer against any listed evaluator in 5 lines of calling code or fewer, with zero imports from Ragas, DeepEval or the model client.
- **SC-002**: 100% of the existing committed evidence entries still resolve under their unchanged keys after the feature ships. This is verified by a full offline run on a cold clone with zero cache misses, zero network attempts and $0.00 spent.
- **SC-003**: The v1.0.0 CLI commands produce byte-identical output and identical exit codes before and after the feature, on the same committed evidence. The saved run summary has the same shape.
- **SC-004**: Across a deliberately mixed batch covering every failure class, 100% of records return a result, zero exceptions escape, and zero failed results carry a numeric score.
- **SC-005**: Scoring the same record twice with the same evaluator and configuration yields results identical in every field except measured latency, with identical fingerprints, and the second call makes no model call.
- **SC-006**: 100% of rubric outputs outside the allowed labels or range are reported as `invalid_output` with the raw judge text kept.
- **SC-007**: Every Ragas evaluation run live on the new path reports token counts greater than zero. No Ragas result on the new path reports 0/0.
- **SC-008**: Listing evaluators succeeds on a fresh install with no environment variables set and no network access.
- **SC-009**: The release ships as v1.1.0, and no existing test needs to change to pass.

## Assumptions

- **Audience.** The "user" here is a developer calling this package as a library, including the downstream platform the research brief proposes. It is not the repo's ten-minute viewer. The viewer's experience (Article 0, Article I's `uv run pytest`) must be unaffected.
- **Mode semantics mirror the existing path.**
  - Offline reads only the evidence store and never calls out.
  - Live calls the judge, records the response and writes it (Article III's miss behaviour), but reports failures as statuses rather than raising.
  - Live is chosen per call by the caller, the same way `EvalSuite(mode=...)` does it today.
- **"Skipped" versus "error".** `skipped` means the evaluator does not apply to this record (a required field is absent). `error` means the evaluator applies but could not produce a verdict: unknown id, cache miss, credential, provider failure, fingerprint mismatch, missing optional install, or ceiling.
- **Fingerprint mismatch is refused, not served.** For built-in evaluators, template changes already move the cache key, because the template is part of the rendered prompt and therefore part of the prompt hash. A stored-versus-current mismatch can therefore only come from decoding parameters or output schema, which the key cannot see. Serving it would break Article III's "anything that moves the output moves the key, or the cache is lying". Refusing it costs one re-run in live mode.
- **Legacy entries are trusted as before.** Entries without a stored fingerprint predate this feature and are served exactly as the old path serves them. The result says so ("not recorded") instead of inventing a fingerprint.
- **Decoding parameters are what is actually sent.** Today no sampling parameter is sent to any call (Article III). The Ragas judge sends a fixed output-token ceiling. The fingerprint records exactly that set, and adding a sampling parameter remains forbidden.
- **Structured output enforcement stays as it is.** This feature does not add NIM `nvext.guided_json` (the research brief recommends it; see the gap analysis). Rubric validation happens on the returned text, and failures surface as `invalid_output`. Adopting `guided_json` later is additive: it changes the fingerprint's output-schema field, not the cache key.
- **Ragas token capture is additive-only.** Counting real tokens on the new path must not change what the existing Ragas cache backend records for the old path. Entries the new path writes may carry real counts; entries the old path writes keep 0/0.
- **Existing call_kinds are reused.** A new-path evaluation of a built-in metric uses the same `call_kind` the old path uses (for example, `ragas:faithfulness`). Identical inputs therefore hit the same committed evidence, which is what makes SC-002 and SC-005 compatible.
- **Latency on a cache hit** is the time to serve from the evidence store, not the original call's latency.
- **Out of scope**: storage of results, datasets, experiments, statistics and comparison across results, tracing, any UI, async, plugin or entry-point discovery, changing where `NIM_BASE_URL` comes from, changing the cache key format, `ToolCorrectness` on the new path, multi-turn records, and `guided_json`.
- **Dependencies**:
  - the existing required model accessors;
  - the hardcoded NIM base URL constant;
  - the existing evidence store and its read and write doors;
  - the existing cost accounting and USD ceiling;
  - the pinned Ragas 0.4.3 and DeepEval 4.2.0;
  - the offline embeddings stub and the author-only calibration install for live `response_relevancy`.

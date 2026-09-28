# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-28

### Added

- **Per-record evaluator contract.** A new `trustnoagent.evaluators.evaluate()` entry point
  scores one `EvalRecord` against one evaluator and returns one `EvalResult`, alongside
  `list_evaluators()`, `REGISTRY`, and `INFOS`. Five built-in evaluators ship: four Ragas
  metrics (`tna.ragas.faithfulness`, `tna.ragas.context_recall`, `tna.ragas.context_precision`,
  `tna.ragas.response_relevancy`) and one DeepEval metric
  (`tna.deepeval.refusal_correctness`) — plus `RubricJudge` for a caller-supplied rubric. A
  malformed or missing judge reply now comes back as a typed `invalid_output` or `error`
  result rather than raising, so a bad judge call no longer aborts a whole eval run.
  `JudgeConfig.from_env()` reads `JUDGE_MODEL` and `GENERATOR_MODEL` always, and
  `NVIDIA_API_KEY` only in live mode. Every result carries a judge fingerprint (model,
  prompt-template version, decoding params, response schema) so a cached score can be told
  apart from one produced by a different judge configuration. A new `compat.yml` workflow
  runs the offline suite against the evaluator contract on every push. None of this changes
  1.0.0 behavior — `evals.cli` and the `trust-no-agent` console script work exactly as before.

### Changed

- **Article II.c amendment.** Only `trustnoagent/evaluators.py` may import both the Ragas and
  DeepEval evaluation layers, and only to route a call to the one evaluator it names — it
  never combines, averages, or compares results across them. The shared contract types
  (`EvalRecord`, `EvalResult`, `RecordField`, …) import neither framework. `CONSTITUTION.md`
  Article II.b is updated to match what the code already did. `tests/test_article_ii_facade.py`
  enforces the import boundary going forward.

### Fixed

- **FR-033: token counts on invalid-output results.** `invalid_output` results used to report
  `tokens=None` even for judge calls that were in fact billed; a live pass caught one such
  case that had actually recorded 157 input and 255 output tokens. These results now report
  the real usage figures from the call that produced them. Regression coverage:
  `tests/test_per_record_ragas_tokens.py` and `tests/test_per_record_rubric_invalid_tokens.py`.

## [1.0.0] - 2026-09-12

Initial release: `trustnoagent`, a facade over Ragas and DeepEval for gating one model's
outputs against another's, packaged for PyPI with a `trust-no-agent` console script.

[1.1.0]: https://github.com/darshan-panchal1/trust-no-agent/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/darshan-panchal1/trust-no-agent/releases/tag/v1.0.0

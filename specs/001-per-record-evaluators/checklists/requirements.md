# Specification Quality Checklist: Per-Record Evaluator Contract

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-26
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). See note 1.
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders. See note 2.
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain. FR-008, FR-032 and FR-040 were resolved 2026-09-26; see spec § Clarifications.
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification. See note 1.

## Notes

1. **Named artifacts are there on purpose.** The spec names env vars (`JUDGE_MODEL`, `GENERATOR_MODEL`, `NVIDIA_API_KEY`), the cache key format, the `call_kind` forms, library pins and constitution articles. Each of these is a hard constraint the request stated as non-negotiable, or a compatibility surface that must not change. They are not design choices the spec is making. No module layout, class names or call mechanics are specified; those belong to `/speckit-plan`.
2. **The audience is developers.** The "user" of this feature is a developer calling a library, so the spec uses developer vocabulary (record, evaluator, cache). It is written at the level of what a caller observes, not how it is built.
3. **Three clarifications were open. All were resolved 2026-09-26, and FR-040 was resolved by the Eleventh amendment (Article II.c):**
   - **FR-040 (governance).** Article II/II.b forbid one entry point routing to both frameworks. This blocks planning, because the answer decides whether this feature carries a constitutional amendment.
   - **FR-008 (scope).** `tna.deepeval.answer_relevancy` has no existing metric or evidence behind it.
   - **FR-032 (data integrity).** It is undecided where live results for caller records are written.
4. Everything else defaulted is recorded under Assumptions: fingerprint-mismatch handling, legacy-entry provenance, the skipped/error split, and no `guided_json`.
5. **Re-validated 2026-09-26 after the evaluator-scope correction.** FR-008 now ships all five metrics v1 scores (`tna.ragas.faithfulness`, `context_recall`, `context_precision`, `response_relevancy`, `tna.deepeval.refusal_correctness`), up from two. Every item above still passes:
   - no clarification markers remain;
   - no artifact still says "two" evaluators;
   - each Ragas id's required fields match its `_required_columns` in ragas 0.4.3, identically in `data-model.md` and `contracts/public-api.md`;
   - FR-011 (no ToolCorrectness) is unaffected;
   - SC-002 still holds, because the three added metrics already have committed evidence under their v1 `call_kind`s (`ragas:faithfulness` 100, `ragas:context_recall` 50, `ragas:context_precision` 175).

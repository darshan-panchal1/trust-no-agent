# Metric attribution

Article IV requires that every separating metric be attributed to exactly one of the three
deliberate axes on which `app/v1_naive` and `app/v2_fixed` differ. This file is that table,
and `tests/test_attribution.py` asserts it names exactly the metrics the separation contract
actually gates on — no more, no fewer.

| Metric | Axis | Role |
|---|---|---|
| `faithfulness` | retrieval | separating gate |
| `context_recall` | retrieval | separating gate |
| `RefusalCorrectness` | prompt | separating gate |
| `ToolCorrectness` | tool | demonstrative only |

The three separating gates are the ones with calibrated bars in `evals/thresholds.yaml`,
enforced by `tests/test_separation_contract.py`. `ToolCorrectness` deliberately has no bar:
Article II.a keeps it demonstrative, because a green tool-correctness number is a statement
about how the metric was configured, not about the agent.

## Attribution here is asserted by construction, not proven by experiment

This is the honest limit of the table above, and it is stated here rather than buried,
because the distinction is the sort of thing an eval harness is supposed to be rigorous
about.

Each row records **which axis was deliberately broken in v1 and is therefore believed
responsible** for that metric's drop. It is not a measurement. `faithfulness` and
`context_recall` are attributed to retrieval because v1's 200-character unoverlapped chunks
at `top_k=2` are the difference that was engineered; `RefusalCorrectness` is attributed to
prompt discipline because v1's system prompt licenses outside knowledge. Neither claim was
isolated experimentally.

Proving attribution would require the full retrieval × prompt 2×2 — four variants, four cache
sets, four live passes, and roughly double the recorded screen time. That was traded away
deliberately for the ten-minute budget in Article 0, and the trade is recorded here so a
later maintainer knows it was a choice and not an oversight.

Anyone who builds the 2×2 replaces this section with the measurement.

## A worked example of why the distinction matters

The regression demo (`evals/ops/regression_demo.py`) edits only the generation prompt and
leaves retrieval byte-identical. `RefusalCorrectness` and `faithfulness` both drop.
`context_recall` does not move — and cannot, because ragas' `LLMContextRecall` reads
`user_input`, `retrieved_contexts` and `reference`, never `response`.

So a metric attributed to *retrieval* was structurally blind to a *prompt*-axis regression.
The attribution above predicted that, and the demo reports `context_recall` as not
applicable rather than claiming it as a third passing gate.

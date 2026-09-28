"""The v1 path's own per-case scores, computed once per session — the reference the
per-record path must reproduce (spec SC-002). Not collected. Reaches the eval layers only
through `evals.ops`, never directly (Article II.c)."""

from __future__ import annotations

from functools import cache

from app.models import AgentResult
from app.v1_naive import answer as v1_answer
from app.v2_fixed import answer as v2_answer
from evals.contract import EvalRecord
from evals.golden.load import load_golden
from evals.golden.schema import GoldenCase
from evals.ops.ragas_means import ragas_results
from evals.ops.refusal_means import Triple, measured

VARIANTS = ("v1_naive", "v2_fixed")


@cache
def answers() -> dict[str, list[AgentResult]]:
    cases = load_golden()
    fns = {"v1_naive": v1_answer, "v2_fixed": v2_answer}
    return {v: [fns[v](case.question, mode="offline") for case in cases] for v in VARIANTS}


@cache
def ragas_scores() -> dict[str, dict[str, list[float]]]:
    """`{variant: {metric: [per-case score, ...]}}`, exactly as `summary_ragas` reads them."""
    results = ragas_results(load_golden(), answers())
    names = ("faithfulness", "context_recall", "context_precision", "response_relevancy")
    return {v: {n: [float(s) for s in results[v][n]] for n in names} for v in VARIANTS}


@cache
def refusal_triples() -> dict[str, list[Triple]]:
    return measured(load_golden(), answers())


def record_for(case: GoldenCase, answer: AgentResult) -> EvalRecord:
    return EvalRecord(
        input=case.question,
        output=answer.answer,
        expected=case.ground_truth,
        contexts=tuple(chunk.text for chunk in answer.retrieved_contexts),
    )

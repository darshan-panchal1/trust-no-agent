"""A caller's rubric judge scoring one record (spec 001, US4). DeepEval side (Article II): the
judge is `evals.judge`'s `CachedJudge`, so the rubric shares the built-ins' client, evidence
store and cost table. Malformed output is `invalid_output` with the judge's text kept (FR-016)."""

from __future__ import annotations

import json

from pydantic import ValidationError

from evals import outcomes
from evals.behavior.record_eval import LIB
from evals.cache import session
from evals.cache.keys import hash_prompt
from evals.contract import EvalRecord, EvalResult
from evals.evaluator import EvaluatorInfo
from evals.failures import failed
from evals.fingerprint import config_fingerprint, result_fingerprint
from evals.judge import build_rubric_judge
from evals.judge.json_completion import RESPONSE_FORMAT
from evals.judge_config import JudgeConfig
from evals.rubric import RubricJudge
from evals.rubric_verdict import render_prompt, verdict_model, verdict_schema


def rubric_info(rubric: RubricJudge, release: str) -> EvaluatorInfo:
    return EvaluatorInfo(rubric.id, f"{release}+{LIB}", rubric.requires, rubric.output_type)


def evaluate_rubric(
    rubric: RubricJudge, info: EvaluatorInfo, record: EvalRecord, judge: JudgeConfig
) -> EvalResult:
    prompt = render_prompt(rubric, record)
    decoding = {"response_format": dict(RESPONSE_FORMAT)}
    template = f"{rubric.id}@{rubric.template_version}"
    config = config_fingerprint(judge.judge_model, template, decoding, verdict_schema(rubric))
    fingerprint = result_fingerprint(config, hash_prompt(prompt))
    with session.begin(config, f"deepeval:judge.{rubric.name}") as active:
        try:
            text = build_rubric_judge(rubric.name, judge.mode).generate(prompt)
        except json.JSONDecodeError as exc:  # json_completion gave up after its one retry
            reason = "the judge never replied with JSON"
            served = dict(active.served)  # FR-033: real, if a retried attempt still wrote one
            return outcomes.invalid(info, reason, exc.doc, judge.judge_model, fingerprint, served)
        except Exception as exc:  # noqa: BLE001 — judge and fingerprint are known: keep them
            return failed(info, exc, judge.judge_model, fingerprint)
        try:
            verdict = verdict_model(rubric).model_validate_json(text)
        except ValidationError as exc:
            reason = f"the judge's reply broke the rubric: {exc.errors()[0]['msg']}"
            served = dict(active.served)  # FR-033: the reply that failed validation, if written
            return outcomes.invalid(info, reason, text, judge.judge_model, fingerprint, served)
        return outcomes.ok(
            info, score=getattr(verdict, "score", None), label=getattr(verdict, "label", None),
            explanation=getattr(verdict, "reason", None), judge_model=judge.judge_model,
            fingerprint=fingerprint, served=dict(active.served),
        )

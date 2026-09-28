"""Judging fingerprints (data-model.md § Fingerprints). The config fingerprint is what a new
cache entry stores beside its key; the result fingerprint adds the rendered prompt. Neither
ever enters the key (Article III, spec FR-028)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping

from evals.cache.keys import hash_prompt
from evals.contract import EvalRecord, RecordField

_SAMPLING = ("temperature", "top_p", "top_k")  # Article III: never sent, so never recorded


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def config_fingerprint(
    judge_model: str, template: str, decoding: Mapping[str, object], schema: object
) -> str:
    """`template` is `"<template_id>@<template_version>"` — never the package version."""
    banned = [name for name in _SAMPLING if name in decoding]
    if banned:
        raise ValueError(f"sampling parameters are banned (Article III): {banned}")
    payload = {"judge_model": judge_model, "template": template, "decoding": dict(decoding)}
    return _sha256(canonical_json({**payload, "schema": schema}))


def result_fingerprint(config_fp: str, prompt_hash: str) -> str:
    return _sha256(f"{config_fp}:{prompt_hash}")


def record_hash(record: EvalRecord, fields: Iterable[RecordField]) -> str:
    """Stands in for the rendered prompt where the framework renders its own internally."""
    values = {name: getattr(record, name) for name in sorted(fields)}
    if isinstance(values.get("contexts"), tuple):
        values["contexts"] = list(values["contexts"])
    return hash_prompt(canonical_json(values))

"""T007: judging fingerprints (data-model.md § Fingerprints) — deterministic, sensitive to
every component, and unable to carry a sampling parameter (Article III)."""

from __future__ import annotations

import hashlib

import pytest

from evals.contract import EvalRecord
from evals.fingerprint import canonical_json, config_fingerprint, record_hash, result_fingerprint

BASE = {"judge_model": "j", "template": "t@1", "decoding": {"max_tokens": 1}, "schema": "s"}


def test_canonical_json_ignores_key_order() -> None:
    assert canonical_json({"b": 1, "a": [2]}) == canonical_json({"a": [2], "b": 1})


def test_config_fingerprint_is_deterministic() -> None:
    assert config_fingerprint(**BASE) == config_fingerprint(**BASE)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [("judge_model", "k"), ("template", "t@2"), ("decoding", {"max_tokens": 2}), ("schema", "z")],
)
def test_every_component_moves_the_fingerprint(field: str, value: object) -> None:
    changed = {**BASE, field: value}
    assert config_fingerprint(**changed) != config_fingerprint(**BASE)  # type: ignore[arg-type]


@pytest.mark.parametrize("banned", ["temperature", "top_p", "top_k"])
def test_a_sampling_parameter_is_refused(banned: str) -> None:
    with pytest.raises(ValueError, match=banned):
        config_fingerprint("j", "t@1", {banned: 0}, "s")


def test_result_fingerprint_binds_config_and_prompt() -> None:
    expected = hashlib.sha256(b"cfg:prompt").hexdigest()
    assert result_fingerprint("cfg", "prompt") == expected


def test_record_hash_covers_only_the_named_fields() -> None:
    record = EvalRecord(input="q", output="a", contexts=("c",))
    other_output = EvalRecord(input="q", output="different", contexts=("c",))
    assert record_hash(record, ("input", "contexts")) == record_hash(
        other_output, ("input", "contexts")
    )
    assert record_hash(record, ("input", "output")) != record_hash(
        other_output, ("input", "output")
    )

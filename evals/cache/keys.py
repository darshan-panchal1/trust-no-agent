"""Cache key derivation (CONSTITUTION.md Article III, FR-029)."""

from __future__ import annotations

import hashlib


def make_key(call_kind: str, model_identity: str, prompt_hash: str) -> str:
    """sha256(call_kind || model_identity || prompt_hash). Nothing else, no exceptions."""
    raw = f"{call_kind}||{model_identity}||{prompt_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_prompt(rendered_prompt: str) -> str:
    """SHA-256 over the fully-rendered prompt, including any system text (FR-029)."""
    return hashlib.sha256(rendered_prompt.encode("utf-8")).hexdigest()

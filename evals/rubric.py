"""A caller-defined rubric judge (spec 001, US4). Framework-free (Article II.c): the definition
only; its prompt and verdict schema are in `evals/rubric_verdict.py`. Validated when made, so a
bad definition is a programming error at the caller's line — never a status later (FR-004)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import get_args

from evals.contract import OutputType, RecordField
from evals.fingerprint import canonical_json

_NAME = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class RubricJudge:
    name: str
    instructions: str
    requires: frozenset[RecordField]
    labels: tuple[str, ...] | None = None
    score_range: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        problems = [
            (not _NAME.match(self.name), f"name must match {_NAME.pattern}"),
            (not self.instructions.strip(), "instructions must not be empty"),
            (not self.requires or not self.requires <= set(get_args(RecordField)),
             f"requires must be a non-empty subset of {get_args(RecordField)}"),
            ((self.labels is None) == (self.score_range is None),
             "set exactly one of labels or score_range"),
            (self.labels is not None and len(set(self.labels or ())) != len(self.labels or ()),
             "labels must be distinct"),
            (self.labels == (), "labels must not be empty"),
            (self.score_range is not None and self.score_range[0] >= self.score_range[1],
             "score_range must run low to high"),
        ]
        if failed := [message for broken, message in problems if broken]:
            raise ValueError(f"invalid RubricJudge {self.name!r}: {'; '.join(failed)}")

    @property
    def id(self) -> str:
        return f"tna.judge.{self.name}"

    @property
    def output_type(self) -> OutputType:
        return "label" if self.labels is not None else "score"

    @property
    def template_version(self) -> str:
        """A content hash: any edit to what the judge is asked moves it (FR-022)."""
        content = {"instructions": self.instructions, "requires": sorted(self.requires),
                   "labels": self.labels, "score_range": self.score_range}
        return hashlib.sha256(canonical_json(content).encode()).hexdigest()[:16]

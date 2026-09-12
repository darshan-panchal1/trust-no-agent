"""Golden dataset loader — JSONL, one case per line (FR-010), corpus cross-check (FR-012)."""

from __future__ import annotations

import json
from pathlib import Path

from app.corpus_loader import list_documents
from evals.golden.schema import GoldenCase

CASES_PATH = Path(__file__).resolve().parent / "cases.jsonl"


def load_golden(path: Path = CASES_PATH) -> list[GoldenCase]:
    """Load and validate every case, including that referenced corpus files exist."""
    corpus_files = set(list_documents())
    cases = []
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        raw = json.loads(line)
        case = GoldenCase.model_validate(raw)
        missing = [f for f in case.reference_contexts if f not in corpus_files]
        if missing:
            raise ValueError(f"cases.jsonl line {line_no}: unknown corpus files {missing}")
        cases.append(case)
    return cases

"""Multi-hop tool-call decision (FR-005) — a question-text heuristic, computed before
retrieval runs, so it cannot depend on whether retrieval happens to succeed or fail.
v1_naive injects two spurious calls on top; v2_fixed calls only what it needs.
"""

from __future__ import annotations

from app.models import RetrievedChunk, ToolCallRecord
from app.tools import cross_reference, lookup_glossary, lookup_policy

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "expenses": ["expense", "per diem", "reimburs"],
    "travel": ["travel", "trip", "flight", "director"],
    "procurement": ["procurement", "vendor", "purchase", "senior manager"],
    "leave": ["leave", "pto", "parental", "sick"],
    "remote": ["remote", "home office"],
    "security": ["security", "password", "device", "loaner"],
}

SPURIOUS_TERMS = ["MFA", "PII"]  # fixed, deterministic — never varies with retrieval outcome


def looks_multi_hop(question: str) -> bool:
    """Purely a function of the question text — two or more policy domains mentioned."""
    lowered = question.lower()
    matched = sum(1 for kws in _DOMAIN_KEYWORDS.values() if any(k in lowered for k in kws))
    return matched >= 2


def decide_tool_calls(
    question: str, contexts: list[RetrievedChunk], inject_spurious: bool
) -> list[ToolCallRecord]:
    if not looks_multi_hop(question):
        return []
    calls: list[ToolCallRecord] = []
    docs = sorted({c.source_document for c in contexts})
    if docs:
        lookup_policy(docs[0])
        calls.append(ToolCallRecord(name="lookup_policy", arguments={"document": docs[0]}))
    if len(docs) >= 2:
        cross_reference(docs[0], docs[1])
        calls.append(
            ToolCallRecord(name="cross_reference", arguments={"doc_a": docs[0], "doc_b": docs[1]})
        )
    if inject_spurious:
        for term in SPURIOUS_TERMS:
            lookup_glossary(term)
            calls.append(ToolCallRecord(name="lookup_glossary", arguments={"term": term}))
    return calls

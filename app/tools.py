"""The three deterministic, local, no-network agent tools.

`cross_reference` is what multi-hop cases need — combining two documents' content so a
question spanning them (e.g. `travel.md` x `procurement.md`) can be answered from one call.
"""

from __future__ import annotations

from app.corpus_loader import read_document

_GLOSSARY: dict[str, str] = {
    "PTO": "Paid Time Off",
    "MFA": "Multi-Factor Authentication",
    "SaaS": "Software as a Service",
    "VP": "Vice President",
    "PII": "Personally Identifiable Information",
}


def lookup_policy(document: str) -> str:
    """Return the full text of one corpus document by filename."""
    return read_document(document)


def lookup_glossary(term: str) -> str:
    """Expand a company-specific abbreviation. Raises KeyError if unknown."""
    if term not in _GLOSSARY:
        raise KeyError(f"unknown glossary term: {term!r}")
    return _GLOSSARY[term]


def cross_reference(doc_a: str, doc_b: str) -> str:
    """Return both documents' content, concatenated, for a multi-hop question spanning them."""
    return f"{read_document(doc_a)}\n\n---\n\n{read_document(doc_b)}"

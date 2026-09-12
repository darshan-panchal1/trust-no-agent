"""T1.6 acceptance: known key returns a value, unknown key raises, no network attempt."""

from __future__ import annotations

import pytest

from app.tools import cross_reference, lookup_glossary, lookup_policy


def test_lookup_policy_known_document_returns_text() -> None:
    assert "Per Diem" in lookup_policy("expenses-v2.md")


def test_lookup_policy_unknown_document_raises() -> None:
    with pytest.raises(FileNotFoundError):
        lookup_policy("does-not-exist.md")


def test_lookup_glossary_known_term_returns_expansion() -> None:
    assert lookup_glossary("PTO") == "Paid Time Off"


def test_lookup_glossary_unknown_term_raises() -> None:
    with pytest.raises(KeyError):
        lookup_glossary("NOPE")


def test_cross_reference_combines_both_documents() -> None:
    combined = cross_reference("travel.md", "procurement.md")
    assert "Director level" in combined
    assert "Seniority Tiers" in combined


@pytest.mark.usefixtures("socket_disabled")
def test_tools_make_no_network_attempt() -> None:
    lookup_policy("travel.md")
    lookup_glossary("VP")
    cross_reference("travel.md", "procurement.md")

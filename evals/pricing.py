"""Loads `pricing.yaml` (FR-034) — this repo's own dated prices, never deepeval's registry.

Article VIII (Eighth amendment): an unpriced model returns `None`, never a fabricated
number and never a silent `$0.00`. No dated Groq price table exists yet (docs/api-notes.md
V5.5-V5.6) — every Groq model currently resolves here, and the caller renders that as
`UNVERIFIED` rather than computing a figure from a third-party estimate.
"""

from __future__ import annotations

import datetime
import functools
from pathlib import Path

import yaml
from pydantic import BaseModel

PRICING_PATH = Path(__file__).resolve().parent / "pricing.yaml"
_PER_MTOK = 1_000_000


class ModelPrice(BaseModel):
    input_per_mtok: float
    output_per_mtok: float
    source: str


class PriceTable(BaseModel):
    # A real date, not a string: a typo'd "checked" is then a loud parse failure rather
    # than a price table that silently claims to have been verified on nonsense.
    checked: datetime.date
    models: dict[str, ModelPrice]


@functools.lru_cache(maxsize=1)
def load_prices(path: Path = PRICING_PATH) -> PriceTable:
    return PriceTable.model_validate(yaml.safe_load(path.read_text()))


def price_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Cost of one call, or `None` if `model` has no row in `pricing.yaml` — never guesses."""
    table = load_prices()
    if model not in table.models:
        return None
    row = table.models[model]
    return (input_tokens * row.input_per_mtok + output_tokens * row.output_per_mtok) / _PER_MTOK

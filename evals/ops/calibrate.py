"""FR-039/040: writes `evals/thresholds.yaml` from committed evidence, entirely offline —
midpoint of the observed v1/v2 gap, for `gate_policy.GATED_METRICS`. A metric under
MARGIN_MIN aborts before anything is written — a partial file fails Article V's schema
test anyway, since it must name every gated metric or none."""

from __future__ import annotations

import yaml

from evals import gate_policy
from evals.ops.observed import observed_means
from evals.thresholds import THRESHOLDS_PATH, Threshold, Thresholds

MARGIN_MIN = 0.05


class NoSeparation(Exception):
    """FR-040: a gated metric showed less than MARGIN_MIN separation — nothing written."""


def _threshold(name: str, v1: float, v2: float) -> Threshold:
    delta = v2 - v1
    print(f"{name:<20} v1={v1:.4f}  v2={v2:.4f}  delta={delta:+.4f}")
    if delta < MARGIN_MIN:
        raise NoSeparation(f"{name}: delta {delta:+.4f} < MARGIN_MIN={MARGIN_MIN}")
    just = f"midpoint of observed v1={v1:.4f}/v2={v2:.4f} (delta {delta:+.4f})"
    return Threshold(value=(v1 + v2) / 2, justification=just, v1_observed=v1, v2_observed=v2)


def build_thresholds(means: dict[str, tuple[float, float]]) -> Thresholds:
    metrics = {name: _threshold(name, *means[name]) for name in gate_policy.GATED_METRICS}
    return Thresholds(
        comparison_tolerance=gate_policy.COMPARISON_TOLERANCE,
        comparison_tolerance_justification=gate_policy.COMPARISON_TOLERANCE_JUSTIFICATION,
        metrics=metrics,
    )


def calibrate() -> Thresholds:
    thresholds = build_thresholds(observed_means())
    THRESHOLDS_PATH.write_text(yaml.dump(thresholds.model_dump(), sort_keys=False))
    return thresholds

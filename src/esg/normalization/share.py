from __future__ import annotations

from typing import Optional


_PERCENT_UNITS = {
    "%",
    "percent",
    "percentage",
}


def normalize_fraction_share(
    value: Optional[float],
    raw_unit: Optional[str],
    canonical_unit: Optional[str],
) -> tuple[Optional[float], str] | None:
    """
    Normalize share disclosures to canonical fraction representation.

    Examples:
      38 %       -> 0.38 fraction
      38 percent -> 0.38 fraction
      0.38 fraction -> 0.38 fraction

    Return None when this is not a fraction-valued KPI or when the
    raw unit does not identify a supported share representation.
    """
    if canonical_unit != "fraction":
        return None

    if value is None or raw_unit is None:
        return None

    unit_token = "".join(raw_unit.split()).lower()

    if unit_token in _PERCENT_UNITS:
        return value / 100.0, "fraction"

    if unit_token == "fraction":
        return value, "fraction"

    return None

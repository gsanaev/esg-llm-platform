from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from esg_user.types import ExtractorResultDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Canonical unit definitions
# ---------------------------------------------------------------------

UNIT_CANONICAL_MAP: Dict[str, str] = {
    # Energy
    "mwh": "MWh",
    "megawatt hours": "MWh",
    "gwh": "MWh",
    "twh": "MWh",
    "kwh": "MWh",

    # Emissions
    "tco2e": "tCO2e",
    "tonnes co2e": "tCO2e",
    "tons co2e": "tCO2e",
    "ktco2e": "tCO2e",
    "mtco2e": "tCO2e",

    # Water
    "m3": "m³",
    "m^3": "m³",
    "m³": "m³",
    "cubic meters": "m³",
}


UNIT_MULTIPLIERS: Dict[str, float] = {
    # Energy → MWh
    "kwh": 1e-3,
    "mwh": 1.0,
    "gwh": 1e3,
    "twh": 1e6,

    # Emissions → tCO2e
    "tco2e": 1.0,
    "ktco2e": 1e3,
    "mtco2e": 1e6,

    # Water → m³
    "m3": 1.0,
    "m^3": 1.0,
    "m³": 1.0,
}


def _canonical_unit(raw_unit: Optional[str]) -> Optional[str]:
    if not raw_unit:
        return None
    return UNIT_CANONICAL_MAP.get(raw_unit.lower(), raw_unit)


def _conversion_multiplier(raw_unit: Optional[str]) -> float:
    if not raw_unit:
        return 1.0
    return UNIT_MULTIPLIERS.get(raw_unit.lower(), 1.0)


# ---------------------------------------------------------------------
# Main normalization entry point
# ---------------------------------------------------------------------


def normalize_kpis(
    extracted: Mapping[str, Any],
) -> Dict[str, ExtractorResultDict]:
    """
    Normalize a loose mapping of KPI → result dict into
    a strict Dict[str, ExtractorResultDict] with:

    - canonical units
    - converted numeric values
    - consistent confidence, source, raw_* fields
    """

    normalized: Dict[str, ExtractorResultDict] = {}

    for code, raw in extracted.items():
        if not isinstance(raw, Mapping):
            raw_dict: Dict[str, Any] = {}
        else:
            raw_dict = dict(raw)

        raw_value = raw_dict.get("value")
        raw_unit = raw_dict.get("unit")
        confidence = float(raw_dict.get("confidence", 0.0))

        # Canonical and converted unit/value
        unit_std = _canonical_unit(raw_unit)
        multiplier = _conversion_multiplier(raw_unit)

        try:
            value_std = float(raw_value) * multiplier if raw_value is not None else None
        except Exception:  # pragma: no cover
            logger.debug("Failed to convert raw_value '%s' for KPI '%s'", raw_value, code)
            value_std = None

        source = raw_dict.get("source", [])
        if not isinstance(source, list):
            source = [str(source)]

        normalized[code] = ExtractorResultDict(
            value=value_std,
            unit=unit_std,
            confidence=confidence,
            source=source,
            raw_value=raw_value,
            raw_unit=raw_unit,
        )

    logger.debug("Normalized KPI results: %s", normalized)
    return normalized

# src/esg/normalization/regex_normalizer.py
from __future__ import annotations

import logging
from typing import Dict, Any, Mapping, Optional

from esg.utils.numeric_parser import parse_scaled_number

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Unit normalization / conversion table
# -----------------------------------------------------------------------------
# We treat the *first* unit in universal_kpis.json as the canonical base unit
# for each KPI. This table lets us convert alternative notations and units
# into that canonical unit.
#
# Example:
#   "kWh" → ("MWh", 1/1000)
#   "GWh" → ("MWh", 1000)
# -----------------------------------------------------------------------------

UNIT_CONVERSIONS = {
    # GHG
    "tco2e": ("tCO2e", 1.0),
    "tco2": ("tCO2e", 1.0),
    "t_co2e": ("tCO2e", 1.0),
    "tonsco2e": ("tCO2e", 1.0),
    "tonnesco2e": ("tCO2e", 1.0),

    # Energy
    "mwh": ("MWh", 1.0),
    "kwh": ("MWh", 1 / 1000),
    "gwh": ("MWh", 1000.0),

    # Water
    "m3": ("m3", 1.0),
    "m³": ("m3", 1.0),
    "cubicmeters": ("m3", 1.0),
    "thousandm3": ("m3", 1000.0),
    "millionm3": ("m3", 1_000_000.0),
}


def _norm_unit_token(u: str) -> str:
    """Lowercase, remove spaces, normalize '³'→'3'."""
    return "".join(u.split()).lower().replace("³", "3")


def _normalize_unit(
    raw_unit: Optional[str],
    canonical_unit: Optional[str],
) -> tuple[Optional[str], float]:
    """
    Map raw_unit → (canonical_unit, multiplier).

    - If canonical_unit is None, we keep the raw_unit and multiplier 1.0.
    - If raw_unit matches canonical_unit (normalized), multiplier = 1.0.
    - If raw_unit is known in UNIT_CONVERSIONS and maps to canonical_unit,
      return that mapping and its multiplier.
    - Otherwise, fall back to canonical_unit with multiplier 1.0.
    """
    if not canonical_unit:
        # No schema unit defined → use raw_unit, no scaling
        return raw_unit, 1.0

    can_norm = _norm_unit_token(canonical_unit)

    if not raw_unit:
        return canonical_unit, 1.0

    u_norm = _norm_unit_token(raw_unit)

    # Exact canonical match
    if u_norm == can_norm:
        return canonical_unit, 1.0

    # Conversion table
    if u_norm in UNIT_CONVERSIONS:
        target_unit, mult = UNIT_CONVERSIONS[u_norm]
        if _norm_unit_token(target_unit) == can_norm:
            return canonical_unit, mult

    # Fallback: keep canonical unit, no scaling
    logger.warning(
        "normalize_regex_result: unsupported unit '%s' (canonical='%s')",
        raw_unit,
        canonical_unit,
    )
    return canonical_unit, 1.0


# -----------------------------------------------------------------------------
# Core normalizer
# -----------------------------------------------------------------------------

def normalize_regex_result(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for regex_extractor output.

    Input per KPI:
        {
            "raw_value": "123,400" or "1.2 million",
            "raw_unit": "tCO2e",
            "confidence": float,
        }

    Behavior:
      - parse_scaled_number(raw_value) for locale + scale ("million", "k", ...)
      - normalize unit into the KPI's canonical base unit (first in schema['units'])
      - apply unit conversion (e.g. kWh → MWh) if needed
    """
    out: Dict[str, Dict[str, Any]] = {}

    for kpi_code, entry in raw_results.items():
        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")

        # Canonical base unit: first unit in schema (if any)
        units = kpi_schema.get(kpi_code, {}).get("units", [])
        canonical_unit = units[0] if units else None

        # --- Numeric parsing (locale + "k"/"million" etc.) ---
        value = parse_scaled_number(raw_value)

        if value is None:
            logger.warning(
                "normalize_regex_result: could not parse raw_value '%s' for KPI '%s'",
                raw_value,
                kpi_code,
            )
            out[kpi_code] = {
                **entry,
                "value": None,
                "unit": canonical_unit,
            }
            continue

        # --- Unit normalization & conversion ---
        unit, factor = _normalize_unit(raw_unit, canonical_unit)
        final_value = value * factor

        out[kpi_code] = {
            **entry,
            "value": final_value,
            "unit": unit,
        }

    return out

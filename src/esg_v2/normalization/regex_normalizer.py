from __future__ import annotations

import logging
import re
from typing import Dict, Any, Optional, Mapping

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Number parsing helpers (Phase 1)
# -----------------------------------------------------------------------------

SCALE_WORDS = {
    "k": 1e3,
    "thousand": 1e3,
    "million": 1e6,
    "m": 1e6,  # sometimes "1.2m" for "million"
}


def _clean_number(text: str) -> Optional[float]:
    """
    Clean human-written numbers while rejecting ambiguous strings.
    """
    compact = text.replace(" ", "")

    # Case 1: Comma-formatted integers: 1,234,567
    if re.fullmatch(r"[0-9]{1,3}(?:,[0-9]{3})+", compact):
        try:
            return float(compact.replace(",", ""))
        except Exception:
            return None

    # Case 2: Simple int/float: 1200000, 1.2, 500
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", compact):
        try:
            return float(compact)
        except Exception:
            return None

    # Fallback: try to extract a single float token
    tokens = re.findall(r"[0-9]+(?:\.[0-9]+)?", compact)
    if len(tokens) == 1:
        try:
            return float(tokens[0])
        except Exception:
            return None

    return None  # ambiguous or invalid


def _detect_scale(text: str) -> float:
    m = re.search(r"(million|thousand|k)\b", text, flags=re.IGNORECASE)
    if not m:
        return 1.0
    return SCALE_WORDS.get(m.group(1).lower(), 1.0)


# -----------------------------------------------------------------------------
# Phase 2 — Unit Normalization Layer
# -----------------------------------------------------------------------------
# canonical_units = the first unit listed in universal_kpis.json per KPI
# conversion_table maps alternative units → conversion factor into base unit
# -----------------------------------------------------------------------------

# "local" conversion table (easily extendable)
UNIT_CONVERSIONS = {
    # GHG
    "tco2e": ("tCO2e", 1.0),
    "t co2e": ("tCO2e", 1.0),
    "tons co2e": ("tCO2e", 1.0),
    "tonnes co2e": ("tCO2e", 1.0),

    # energy
    "mwh": ("MWh", 1.0),
    "kwh": ("MWh", 1/1000),
    "gwh": ("MWh", 1000),

    # water
    "m3": ("m3", 1.0),
    "m³": ("m3", 1.0),
    "cubic meters": ("m3", 1.0),
    "thousand m3": ("m3", 1000),
    "million m3": ("m3", 1_000_000),
}


def _normalize_unit(raw_unit: str, kpi_code: str, canonical_unit: str) -> Optional[tuple[str, float]]:
    """
    Returns: (canonical_unit, multiplier) or None if incompatible.
    """
    u = raw_unit.strip().lower()

    # Exact match (case-insensitive)
    if u == canonical_unit.lower():
        return canonical_unit, 1.0

    # Lookup in conversion table
    if u in UNIT_CONVERSIONS:
        target_unit, mult = UNIT_CONVERSIONS[u]

        # Only accept if conversion target matches KPI canonical unit
        if target_unit.lower() == canonical_unit.lower():
            return canonical_unit, mult

    # No compatible conversion found
    logger.warning(
        "normalize_regex_result_v2: unsupported unit '%s' for KPI '%s' (base='%s')",
        raw_unit, kpi_code, canonical_unit
    )
    return None


# -----------------------------------------------------------------------------
# Core normalizer (Phase 1 + Phase 2 combined)
# -----------------------------------------------------------------------------

def normalize_regex_result_v2(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Phase 2 normalizer:
    - parses number (Phase 1)
    - applies scale words (Phase 1)
    - converts units to canonical base units (Phase 2)
    """
    out: Dict[str, Dict[str, Any]] = {}

    for kpi_code, entry in raw_results.items():
        raw_value = entry.get("raw_value", "")
        raw_unit = entry.get("raw_unit", "")
        base_unit = kpi_schema[kpi_code]["units"][0]  # canonical base

        # --- Phase 1 numeric parsing ---
        scale = _detect_scale(raw_value)
        num = _clean_number(raw_value)

        if num is None:
            logger.warning(
                "normalize_regex_result_v2: could not parse raw_value '%s' for KPI '%s'",
                raw_value, kpi_code
            )
            out[kpi_code] = {**entry, "value": None, "unit": base_unit}
            continue

        # --- Phase 2 unit normalization ---
        unit_info = _normalize_unit(raw_unit, kpi_code, base_unit)
        if not unit_info:
            # unsupported unit — keep numeric part, but unit becomes base
            out[kpi_code] = {
                **entry,
                "value": num * scale,
                "unit": base_unit,
            }
            continue

        canonical_unit, unit_factor = unit_info

        # --- Final numeric value ---
        final_value = num * scale * unit_factor

        out[kpi_code] = {
            **entry,
            "value": final_value,
            "unit": canonical_unit,
        }

    return out

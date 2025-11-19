# src/esg/normalization/table_plain_normalizer.py
from __future__ import annotations

from typing import Any, Dict, Mapping

from esg.utils.numeric_parser import parse_locale_number


def _norm_unit(u: str) -> str:
    """Normalize unit for comparison."""
    return "".join(u.split()).lower().replace("³", "3")


def normalize_table_plain_result(
    raw_results: Dict[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for table_plain_extractor output.

    Input per KPI:
        {
            "raw_value": "123,400",
            "raw_unit": "tCO2e" or None,
            "confidence": float,
        }

    Behavior:
        - parse_locale_number(raw_value)
        - resolve unit to one of the schema's allowed units
        - if raw_unit is missing but there is exactly one allowed unit,
          use that unit deterministically
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = float(entry.get("confidence", 0.5))

        # ---- Numeric parsing ----
        value = parse_locale_number(raw_value)

        # ---- Unit resolution ----
        allowed_units = kpi_schema.get(code, {}).get("units", [])
        unit = None

        if raw_unit and allowed_units:
            ru = _norm_unit(raw_unit)
            for u in allowed_units:
                if ru == _norm_unit(u):
                    unit = u
                    break

        # If still missing and there is exactly one allowed unit
        if unit is None and len(allowed_units) == 1:
            unit = allowed_units[0]

        normalized[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

    return normalized

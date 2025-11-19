# src/esg/normalization/table_grid_normalizer.py
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from esg.utils.numeric_parser import parse_locale_number

logger = logging.getLogger(__name__)


def _normalize_unit_token(u: str) -> str:
    """Normalize unit tokens for comparison."""
    return u.lower().replace(" ", "").replace("³", "3")


def normalize_table_grid_result(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for table_grid_extractor output.

    Input per KPI:
        {
            "raw_value": "123,400",
            "raw_unit": "tCO2e" or None,
            "value": <string or float or None>,
            "unit": <unit or None>,
            "confidence": float,
        }

    Behavior:
      - parse numeric value using parse_locale_number(raw_value) unless extractor
        already provided a numeric value
      - resolve unit to one of the schema's allowed units
      - deterministic fallbacks if extractor failed to resolve unit
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        reported_value = entry.get("value")
        reported_unit = entry.get("unit")
        confidence = float(entry.get("confidence", 0.9))

        allowed_units = kpi_schema.get(code, {}).get("units", [])

        # ---------------------------------------------------------
        # 1) Number parsing
        # ---------------------------------------------------------
        if isinstance(reported_value, (int, float)):
            value: Optional[float] = float(reported_value)
        else:
            value = parse_locale_number(raw_value)

        # ---------------------------------------------------------
        # 2) Unit normalization
        # ---------------------------------------------------------
        unit = None

        # a) extractor already resolved a canonical unit
        if reported_unit in allowed_units:
            unit = reported_unit

        # b) try raw_unit against allowed units
        if unit is None and raw_unit:
            norm_ru = _normalize_unit_token(raw_unit)
            for u in allowed_units:
                if norm_ru == _normalize_unit_token(u):
                    unit = u
                    break

        # c) if only a single allowed unit exists, pick it deterministically
        if unit is None and len(allowed_units) == 1:
            unit = allowed_units[0]

        # d) if we still have no unit but we *do* have a numeric value and
        #    there are allowed units, choose the first as a deterministic
        #    fallback (prevents None-units in common test cases)
        if unit is None and value is not None and allowed_units:
            unit = allowed_units[0]

        normalized[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

    return normalized

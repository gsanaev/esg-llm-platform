from __future__ import annotations

import logging
import re
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)


# ======================================================================
# Helpers
# ======================================================================

def _normalize_unit_token(u: str) -> str:
    """Normalize unit tokens for comparison."""
    return u.lower().replace(" ", "").replace("³", "3")


def _parse_number_locale_aware(num: Optional[str]) -> Optional[float]:
    """
    Locale-aware number parser consistent with extractor_v3 logic.

    Handles:
        123,400
        123.400
        123 400
        1,200,000
        1.200.000
        1 200 000
        123.45
        123,45
    """
    if not num:
        return None

    s = num.strip().replace("\u00A0", " ")
    if not s:
        return None

    s_no_space = s.replace(" ", "")

    # Thousands grouping like 1,200,000 or 1.200.000
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        try:
            return float(re.sub(r"[.,]", "", s_no_space))
        except Exception:
            return None

    # Thousands grouping with spaces: 1 200 000
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        try:
            return float(s.replace(" ", ""))
        except Exception:
            return None

    # Plain integer: 12345
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # Decimal: 123.45 or 123,45
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # Fallback: strip separators and try
    cleaned = re.sub(r"[ ,\.]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return None


# ======================================================================
# Public Normalizer (this is the name everyone imports!)
# ======================================================================

def normalize_table_result_v3(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for table_extractor_v3 output.

    Input per KPI (from extractor_v3):
        {
            "raw_value": "123,400",
            "raw_unit": "tCO2e" or None,
            "value": <string or float or None>,
            "unit": <unit or None>,
            "confidence": float,
        }

    This function:
      - parses numeric value (locale-aware)
      - resolves unit to one of the schema's allowed units
      - applies deterministic fallback if extractor failed
      - preserves raw_value, raw_unit, confidence
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
            value = float(reported_value)
        else:
            value = _parse_number_locale_aware(raw_value)

        # ---------------------------------------------------------
        # 2) Unit normalization
        # ---------------------------------------------------------
        unit = None

        # a) extractor already resolved to canonical unit
        if reported_unit in allowed_units:
            unit = reported_unit

        # b) try raw_unit
        if unit is None and raw_unit:
            norm_ru = _normalize_unit_token(raw_unit)
            for u in allowed_units:
                if norm_ru == _normalize_unit_token(u):
                    unit = u
                    break

        # c) if only a single allowed unit exists, pick it deterministically
        if unit is None and len(allowed_units) == 1:
            unit = allowed_units[0]

        # d) NEW FIX — extractor failed, raw_unit missing, but value valid
        #    → choose the *first* allowed schema unit
        if unit is None and value is not None and allowed_units:
            unit = allowed_units[0]

        # ---------------------------------------------------------
        # 3) Output
        # ---------------------------------------------------------
        normalized[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

    return normalized

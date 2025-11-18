# src/esg_v2/normalization/table_normalizer_v2.py
from __future__ import annotations

from typing import Any, Dict, Mapping
import re


# ------------------------------------------------------------
# Robust but minimal number parser (EU/US formats)
# ------------------------------------------------------------
def _clean_number(num: str | None) -> float | None:
    if not num:
        return None

    s = num.strip().replace("\u00A0", " ")  # non-breaking space
    if not s:
        return None

    # Remove spaces
    s_no_space = s.replace(" ", "")

    # --- Case A: 1,200,000 or 1.200.000 ---
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        digits = re.sub(r"[.,]", "", s_no_space)
        try:
            return float(digits)
        except Exception:
            return None

    # --- Case B: 1 200 000 ---
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        digits = s.replace(" ", "")
        try:
            return float(digits)
        except Exception:
            return None

    # --- Case C: Decimal 123.45 or 123,45 ---
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # --- Case D: Simple integer ---
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # Fallback: remove obvious separators
    digits = re.sub(r"[ .,]", "", s)
    try:
        return float(digits)
    except Exception:
        return None


# ------------------------------------------------------------
# Table v2 Normalization
# ------------------------------------------------------------
def normalize_table_result_v2(
    raw_results: Dict[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    normalized = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = entry.get("confidence", 0.5)

        # ---- Numeric parsing ----
        value = _clean_number(raw_value)

        # ---- Unit resolution ----
        canonical_units = kpi_schema[code].get("units", [])
        unit = None

        if raw_unit and canonical_units:
            ru = "".join(raw_unit.split()).lower().replace("³", "3")
            for cu in canonical_units:
                cu_norm = "".join(cu.split()).lower().replace("³", "3")
                if ru == cu_norm:
                    unit = cu
                    break

        # If unit missing and KPI has exactly one canonical unit
        if unit is None and len(canonical_units) == 1:
            unit = canonical_units[0]

        normalized[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

    return normalized

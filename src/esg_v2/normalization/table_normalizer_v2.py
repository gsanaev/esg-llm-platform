# src/esg_v2/normalization/table_normalizer_v2.py
from __future__ import annotations

from typing import Any, Dict, Mapping


def _clean_number(num: str | None) -> float | None:
    if not num:
        return None

    s = num.strip().lower()
    s = s.replace(" ", "")

    # -----------------------------
    # 1) Handle European formats
    # -----------------------------
    if "," not in s:
        parts = s.split(".")
        # Case like 1.200.000 → pure thousand separators
        if len(parts) > 2:
            try:
                return float("".join(parts))
            except Exception:
                pass

        # Case like 500.000 → 500000 if last group has 3 digits
        if len(parts) == 2 and len(parts[1]) == 3:
            try:
                return float(parts[0] + parts[1])
            except Exception:
                pass

    # -----------------------------
    # 2) Remove separators for normal parsing
    # -----------------------------
    s = s.replace(",", "").replace(".", "")

    try:
        return float(s)
    except Exception:
        return None


def normalize_table_result_v2(
    raw_results: Dict[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize table_v2 extraction:
    - parse raw_value to numeric
    - resolve raw_unit to canonical KPI unit if possible
    - preserve confidence
    """
    normalized = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = entry.get("confidence", 0.5)

        # Parse numeric
        value = _clean_number(raw_value)

        # Resolve unit
        canonical_units = kpi_schema[code].get("units", [])
        unit = None

        if raw_unit and canonical_units:
            ru = raw_unit.lower().replace("³", "3").replace(" ", "")
            for cu in canonical_units:
                cu_norm = cu.lower().replace("³", "3").replace(" ", "")
                if ru == cu_norm:
                    unit = cu
                    break

        normalized[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

    return normalized

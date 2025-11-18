# src/esg_v2/normalization/llm_normalizer_v2.py
from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional


def _norm_unit_token(u: str) -> str:
    return u.lower().replace(" ", "").replace("³", "3")


def _parse_llm_number(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None

    s = raw.strip().lower()
    s = s.replace("\u00A0", " ")

    # "1.2 million"
    m = re.match(r"([\d.,]+)\s*million", s)
    if m:
        base = m.group(1).replace(",", "")
        try:
            return float(base) * 1_000_000
        except Exception:
            return None

    # "1.2 thousand"
    m = re.match(r"([\d.,]+)\s*thousand", s)
    if m:
        base = m.group(1).replace(",", "")
        try:
            return float(base) * 1000
        except Exception:
            return None

    # Remove spaces
    s = s.replace(" ", "")

    # Thousands separators
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s):
        try:
            return float(re.sub(r"[.,]", "", s))
        except Exception:
            return None

    # Decimal
    if re.match(r"^\d+[.,]\d+$", s):
        try:
            return float(s.replace(",", "."))
        except Exception:
            return None

    # Fallback: strip punctuation
    cleaned = re.sub(r"[ ,\.]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return None


def normalize_llm_result_v2(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:

    normalized = {}

    for code, entry in raw_results.items():
        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = entry.get("confidence", 0.75)

        allowed_units = kpi_schema.get(code, {}).get("units", [])
        value = _parse_llm_number(raw_value)

        # Unit resolution
        unit = None
        if raw_unit:
            ru = _norm_unit_token(raw_unit)
            for u in allowed_units:
                if ru == _norm_unit_token(u):
                    unit = u
                    break

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

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional


# ----------------------------------------------------------------------
# Shared helpers (same behavior as regex_normalizer)
# ----------------------------------------------------------------------
def _clean_number(num: Optional[str]) -> Optional[float]:
    """
    Locale-aware numeric cleaning, consistent with regex_normalizer.
    Supports: "123,400", "123.400", "1 200 000", "1.200.000", "1,200,000".
    """
    if not num:
        return None

    s = num.strip().replace("\u00A0", " ")

    # remove spaces for easier logic
    s_no_space = s.replace(" ", "")

    # 1) 1,200,000 or 1.200.000 → remove separators
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        try:
            return float(re.sub(r"[.,]", "", s_no_space))
        except Exception:
            return None

    # 2) 1 200 000 → remove spaces
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        try:
            return float(s.replace(" ", ""))
        except Exception:
            return None

    # 3) integer
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # 4) decimal: 123.45 or 123,45
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # fallback: remove punctuation and parse
    cleaned = re.sub(r"[ ,\.]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return None


def _normalize_unit_token(u: str) -> str:
    """Normalize units: lowercase, remove spaces, unify '³'→'3'."""
    return u.lower().replace(" ", "").replace("³", "3")


# ----------------------------------------------------------------------
# NLP normalizer (same interface as regex normalizer)
# ----------------------------------------------------------------------
def normalize_nlp_result_v2(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for NLP extractor output.

    Input format (same as regex extractor):
        {
            "raw_value": "123,400",
            "raw_unit": "tCO2e",
            "confidence": <float>,
        }

    Output:
        - parsed float value
        - canonical unit (if possible)
        - keeps confidence
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = float(entry.get("confidence", 0.6))

        allowed_units = kpi_schema.get(code, {}).get("units", [])

        # ---- Value parsing ----
        value = _clean_number(raw_value)

        # ---- Unit resolution ----
        unit = None

        if raw_unit:
            ru_norm = _normalize_unit_token(raw_unit)
            for u in allowed_units:
                if ru_norm == _normalize_unit_token(u):
                    unit = u
                    break

        # fallback: single allowed unit
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

# src/esg/normalization/nlp_normalizer.py
from __future__ import annotations

from typing import Any, Dict, Mapping

from esg.utils.numeric_parser import parse_scaled_number


def _norm_unit_token(u: str) -> str:
    """Normalize units: lowercase, remove spaces, unify '³'→'3'."""
    return u.lower().replace(" ", "").replace("³", "3")


def normalize_nlp_result(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for NLP extractor (extract_kpis_nlp) output.

    Input format (per KPI):
        {
            "raw_value": "123,400" or "1.2 million",
            "raw_unit": "tCO2e",
            "confidence": <float>,
        }

    Behavior:
        - parse_scaled_number(raw_value) for locale + "million"/"k" scale
        - resolve unit to one of the schema's allowed units
        - if raw_unit is missing and there is exactly one allowed unit, use it
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = float(entry.get("confidence", 0.65))

        allowed_units = kpi_schema.get(code, {}).get("units", [])

        # ---- Value parsing (locale + scaling words) ----
        value = parse_scaled_number(raw_value)

        # ---- Unit resolution ----
        unit = None

        if raw_unit:
            ru_norm = _norm_unit_token(raw_unit)
            for u in allowed_units:
                if ru_norm == _norm_unit_token(u):
                    unit = u
                    break

        # deterministic fallback if there is only one allowed unit
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

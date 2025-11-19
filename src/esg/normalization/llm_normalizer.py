# src/esg/normalization/llm_normalizer.py
from __future__ import annotations

from typing import Any, Dict, Mapping

from esg.utils.numeric_parser import parse_scaled_number


def _norm_unit_token(u: str) -> str:
    return u.lower().replace(" ", "").replace("³", "3")


def normalize_llm_result(
    raw_results: Mapping[str, Dict[str, Any]],
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalizer for LLM extractor (extract_kpis_llm) output.

    Input per KPI:
        {
            "raw_value": "123,400" or "1.2 million",
            "raw_unit": "tCO2e" | "MWh" | "m3" | ...,
            "confidence": float,
        }

    Behavior:
        - parse_scaled_number(raw_value) (supports locale + "million"/"thousand"/"k")
        - map raw_unit to one of the KPI's allowed units
        - if there is exactly one allowed unit and we can't match raw_unit,
          use that unit deterministically
    """
    normalized: Dict[str, Dict[str, Any]] = {}

    for code, entry in raw_results.items():
        if not entry:
            continue

        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")
        confidence = float(entry.get("confidence", 0.75))

        allowed_units = kpi_schema.get(code, {}).get("units", [])

        # ---- Value parsing (with scaling) ----
        value = parse_scaled_number(raw_value)

        # ---- Unit resolution ----
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

# src/esg/normalization/llm_normalizer.py
from __future__ import annotations

from typing import Any, Dict, Mapping

from esg.utils.numeric_parser import parse_scaled_number
from esg.normalization.scoring import compute_extraction_score

from esg.core.schema import (
    get_accepted_units,
    get_canonical_unit,
)
from esg.normalization.share import normalize_fraction_share

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

        meta = kpi_schema.get(code, {})
        value_type = str(
            meta.get("value_type", "quantitative")
        )

        allowed_units = get_accepted_units(meta)
        canonical_unit = get_canonical_unit(meta)

        # ---- Value normalization ----
        if value_type == "qualitative":
            if raw_value is None:
                value = None
            else:
                normalized_text = " ".join(
                    str(raw_value).split()
                ).strip()

                value = (
                    normalized_text.lower()
                    if normalized_text
                    else None
                )

            unit = None

        else:
            value = parse_scaled_number(raw_value)

            share_result = normalize_fraction_share(
                value,
                raw_unit,
                canonical_unit,
            )

            if share_result is not None:
                value, unit = share_result

            else:
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

        normalized_entry = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
        }

        normalized_entry["_score"] = compute_extraction_score(
            parsed_value=value,
            unit=unit,
            allowed_units=allowed_units,
            base_confidence=confidence,
            source="llm",
        )

        normalized[code] = normalized_entry


    return normalized

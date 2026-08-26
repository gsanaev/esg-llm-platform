# src/esg/normalization/table_grid_normalizer.py
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional

from esg.utils.numeric_parser import parse_locale_number
from esg.normalization.scoring import compute_extraction_score

from esg.core.schema import (
    get_accepted_units,
    get_canonical_unit,
)
from esg.normalization.share import normalize_fraction_share

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

        meta = kpi_schema.get(code, {})
        value_type = str(
            meta.get("value_type", "quantitative")
        )

        allowed_units = get_accepted_units(meta)
        canonical_unit = get_canonical_unit(meta)

        # ---------------------------------------------------------
        # 1) Value normalization
        # ---------------------------------------------------------
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
            # -----------------------------------------------------
            # Quantitative number parsing
            # -----------------------------------------------------
            if isinstance(reported_value, (int, float)):
                value: Optional[float] = float(reported_value)
            else:
                value = parse_locale_number(raw_value)

            # -----------------------------------------------------
            # Quantitative unit normalization
            # -----------------------------------------------------
            share_result = normalize_fraction_share(
                value,
                raw_unit,
                canonical_unit,
            )

            if share_result is not None:
                value, unit = share_result
            else:
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

                # c) if only a single allowed unit exists, pick it
                #    deterministically
                if unit is None and len(allowed_units) == 1:
                    unit = allowed_units[0]

                # d) deterministic fallback for quantitative KPIs
                if (
                    unit is None
                    and value is not None
                    and allowed_units
                ):
                    unit = allowed_units[0]

        normalized_entry = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "value": value,
            "unit": unit,
            "confidence": confidence,
            "page": entry.get("page"),
            "source_context": entry.get("source_context"),
            "location": entry.get("location"),
            "year": entry.get("year"),
        }

        # Internal score for debugging / analysis (does not affect confidence)
        normalized_entry["_score"] = compute_extraction_score(
            parsed_value=value,
            unit=unit,
            allowed_units=allowed_units,
            base_confidence=confidence,
            source="table_grid",
        )

        normalized[code] = normalized_entry


    return normalized

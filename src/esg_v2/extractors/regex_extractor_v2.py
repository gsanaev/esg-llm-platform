# src/esg_v2/extractors/regex_extractor_v2.py
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, Any, Mapping

logger = logging.getLogger(__name__)


# =====================================================================
# Cached regex builder
# =====================================================================

@lru_cache(maxsize=256)
def _cached_pattern(units_key: str) -> re.Pattern:
    """
    Build a number+unit pattern and cache it.
    units_key = "unit1||unit2||unit3"
    """
    units = units_key.split("||")
    unit_regex = "|".join(re.escape(u) for u in units)

    number_like = r"""
        (?P<value>
            [0-9][0-9,\.\s]*         # digits with separators
            (?:million|thousand|k)?  # optional scale word
        )
    """

    pattern = rf"""
        {number_like}
        \s*
        (?P<unit>{unit_regex})
    """

    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


def _get_pattern(units: list[str]) -> re.Pattern:
    """Return cached full regex pattern for KPI units."""
    return _cached_pattern("||".join(units))


# =====================================================================
# Main extractor (fully minimal)
# =====================================================================

def extract_kpis_regex_v2(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:
    """
    Minimal, stable regex extractor:
    - Finds simple number + unit patterns
    - No numeric interpretation here (normalizer handles it)
    - Returns raw_value + raw_unit only
    - Takes first match only (first-hit rule)
    - Uses only schema['units']
    """
    results: Dict[str, Dict[str, Any]] = {}

    # Normalize whitespace to avoid regex failing across lines
    cleaned = re.sub(r"\s+", " ", text)

    for kpi_code, meta in kpi_schema.items():
        units = meta.get("units") or []
        if not units:
            # Quiet skip — some KPIs may not be regex-detectable
            continue

        pattern = _get_pattern(units)
        match = pattern.search(cleaned)
        if not match:
            continue

        raw_value = match.group("value").strip()
        raw_unit = match.group("unit").strip()

        logger.info("regex_v2 hit %s: %s %s", kpi_code, raw_value, raw_unit)

        results[kpi_code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "confidence": base_confidence,
        }

    return results

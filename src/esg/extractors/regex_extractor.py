# src/esg/extractors/regex_extractor.py
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
    Build and cache a number+unit pattern.

    Parameters
    ----------
    units_key:
        String key joining unit tokens, e.g. "tCO2e||m3||MWh".

    Returns
    -------
    re.Pattern
        Compiled regex with groups:
            - 'value': the numeric-like part (with optional scale word)
            - 'unit' : the matched unit token
    """
    # Split back into units (they are joined with "||")
    units = [u for u in units_key.split("||") if u]

    # Safety: if somehow empty, compile a pattern that never matches
    if not units:
        return re.compile(r"(?!x)x")

    # Deduplicate units to avoid redundant branches
    units = list(dict.fromkeys(units))

    unit_regex = "|".join(re.escape(u) for u in units)

    # Numeric-like token with optional scale word
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
    """
    Return cached full regex pattern for a list of units.

    Parameters
    ----------
    units:
        List of unit strings exactly as they appear in text
        (e.g. ["tCO2e", "m³"]).
    """
    # Join with a separator that will not appear inside units
    units_key = "||".join(units)
    return _cached_pattern(units_key)


# =====================================================================
# Main extractor (minimal, stable)
# =====================================================================

def extract_kpis_regex(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:
    """
    Minimal, stable regex extractor.

    Responsibilities:
    - Find simple "<number> <unit>" patterns in plain text.
    - Do *not* interpret/convert numbers (normalizer handles that).
    - Return:
        {
            kpi_code: {
                "raw_value": str,
                "raw_unit": str,
                "confidence": float,
            },
            ...
        }
    - Enforce a first-hit rule: only the *first* occurrence per KPI.
    - Use only the 'units' field from the KPI schema.
    """
    results: Dict[str, Dict[str, Any]] = {}

    if not text:
        return results

    # Normalize whitespace so patterns are not broken by newlines
    cleaned = re.sub(r"\s+", " ", text)

    for kpi_code, meta in kpi_schema.items():
        # Pull unit list from schema; skip KPIs without units
        units = meta.get("units") or []
        if not units:
            continue

        pattern = _get_pattern(units)
        match = pattern.search(cleaned)
        if not match:
            continue

        raw_value = match.group("value").strip()
        raw_unit = match.group("unit").strip()

        logger.info("regex hit %s: %s %s", kpi_code, raw_value, raw_unit)

        results[kpi_code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "confidence": base_confidence,
        }

    return results

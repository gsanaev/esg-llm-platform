# src/esg/extractors/regex_extractor.py
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, Any, Mapping

logger = logging.getLogger(__name__)


# =====================================================================
# Cached regex builder (value-first)
# =====================================================================

@lru_cache(maxsize=256)
def _pattern_value_first(units_key: str) -> re.Pattern:
    units = [u for u in units_key.split("||") if u]
    if not units:
        return re.compile(r"(?!x)x")

    unit_regex = "|".join(re.escape(u) for u in units)

    pattern = rf"""
        (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        \s*
        (?P<unit>{unit_regex})
    """
    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


# =====================================================================
# Pattern B: "(unit) value"
# =====================================================================

def _pattern_paren_unit_first(units: list[str]) -> re.Pattern:
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""\(
                (?P<unit>{unit_regex})
            \)
            \s*(?:of|is|=|:)?\s*
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        """,
        re.IGNORECASE | re.VERBOSE
    )


# =====================================================================
# Pattern C: "unit value" (NO parentheses)
# =====================================================================

def _pattern_unit_first(units: list[str]) -> re.Pattern:
    """
    Matches: "tCO2e 123,400" but avoids matching inside e.g. "(tCO2e)"
    """
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""
            (?<!\()                      # cannot be inside parentheses
            (?P<unit>{unit_regex})
            \s*
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        """,
        re.IGNORECASE | re.VERBOSE
    )

# =====================================================================
# Pattern D: "(unit) ... value" within max window (120 chars)
# =====================================================================

def _pattern_paren_unit_near_value(units: list[str], max_window: int = 120) -> re.Pattern:
    """
    Matches cases like:
        "(tCO2e) ... was 123,400"
        "(MWh) ... amounted to 500,000,"
        "(m3) ... is around 1,200,000."
    where the distance between ')' and the value is <= max_window characters.

    Trailing punctuation after the value is allowed.
    """
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""
            \(
                (?P<unit>{unit_regex})
            \)
            (?P<middle>.{{0,{max_window}}}?)        # up to 120 chars
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
            \s*[,;.]?                                # optional trailing punctuation
        """,
        re.IGNORECASE | re.VERBOSE
    )


# =====================================================================
# Public getter for pattern A
# =====================================================================

def _get_pattern_value_first(units: list[str]) -> re.Pattern:
    return _pattern_value_first("||".join(units))


# =====================================================================
# Main extractor
# =====================================================================

def extract_kpis_regex(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:

    results: Dict[str, Dict[str, Any]] = {}
    if not text:
        return results

    cleaned = re.sub(r"\s+", " ", text)

    for code, meta in kpi_schema.items():
        units = meta.get("units") or []
        if not units:
            continue

        # Build 3 patterns
        pA = _get_pattern_value_first(units)
        pB = _pattern_paren_unit_first(units)
        pC = _pattern_unit_first(units)

        # Try A: "<value> <unit>"
        mA = pA.search(cleaned)
        if mA:
            v = mA.group("value").strip()
            u = mA.group("unit").strip()
            logger.info("regex hit %s (A value-unit): %s %s", code, v, u)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue

        # Try B: "(<unit>) <value>"
        mB = pB.search(cleaned)
        if mB:
            v = mB.group("value").strip()
            u = mB.group("unit").strip()
            logger.info("regex hit %s (B paren-unit-value): (%s) %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue

        # Try C: "<unit> <value>" (no parentheses)
        mC = pC.search(cleaned)
        if mC:
            v = mC.group("value").strip()
            u = mC.group("unit").strip()
            logger.info("regex hit %s (C unit-value): %s %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue


        # Try D: "(<unit>) ... <value>" (window-limited)
        pD = _pattern_paren_unit_near_value(units, max_window=120)
        mD = pD.search(cleaned)
        if mD:
            v = mD.group("value").strip().rstrip(".,;")
            u = mD.group("unit").strip()
            logger.info("regex hit %s (D paren-unit-near-value): (%s) ... %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue


    return results

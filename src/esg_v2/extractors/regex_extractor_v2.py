# src/esg_v2/extractors/regex_extractor_v2.py
from __future__ import annotations

import logging
import re
from typing import Dict, Any, Mapping

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _build_pattern_for_kpi(kpi_name: str, units: list[str]) -> re.Pattern:
    """
    Build a safe, non-greedy regex pattern for a KPI.
    The pattern captures strings like:

    "123,400 tCO2e"
    "1.2 million m3"
    "500000 MWh"
    """

    # Join units into a single alternation group, e.g. (tCO2e|tco2e|tCOne)
    unit_regex = "|".join(re.escape(u) for u in units)

    # Raw value pattern (does NOT interpret numbers)
    number_like = r"([0-9][0-9,.\s]*(?:million|thousand|k)?)"

    # Full pattern:
    #   KPI name ... number ... unit
    pattern = rf"""
        (?P<value>{number_like})         # captured raw numeric text
        \s*
        (?P<unit>{unit_regex})           # one of the allowed units
    """

    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


# ------------------------------------------------------------
# Main extractor
# ------------------------------------------------------------

def extract_kpis_regex_v2(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:
    """
    New v2 regex extractor.
    - Does NOT parse numbers
    - Does NOT multiply values incorrectly
    - Returns raw_value + raw_unit as strings

    Parameters
    ----------
    text : str
        Raw PDF text (cleaned)
    kpi_schema : dict
        Loaded from universal_kpis.json
        Example entry:
            {
              "display_name": "Total GHG Emissions",
              "units": ["tCO2e", "tco2e", "TCOne"]
            }

    Returns
    -------
    dict: {kpi_code: {raw_value, raw_unit, confidence}}
    """

    results: Dict[str, Dict[str, Any]] = {}

    for kpi_code, meta in kpi_schema.items():
        units = meta.get("units", [])
        if not units:
            logger.warning("v2 regex extractor: KPI '%s' has no units; skipping", kpi_code)
            continue

        pattern = _build_pattern_for_kpi(kpi_code, units)

        match = pattern.search(text)
        if not match:
            continue

        raw_value = match.group("value").strip()
        raw_unit = match.group("unit").strip()

        logger.info("v2 regex hit for %s: raw_value='%s', raw_unit='%s'",
                    kpi_code, raw_value, raw_unit)

        results[kpi_code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "confidence": base_confidence,
        }

    return results

from __future__ import annotations

import logging
import re
from typing import Dict, Any, Mapping

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Build KPI-specific number–unit regex
# ------------------------------------------------------------

def _build_pattern_for_kpi(units: list[str]) -> re.Pattern:
    """
    Return a regex that captures:
        "123,400 tCO2e"
        "1.2 million m3"
        "500000 MWh"
    The pattern is intentionally simple and stable.
    """
    unit_regex = "|".join(re.escape(u) for u in units)

    number_like = r"""
        (?P<value>
          [0-9][0-9,\.\s]*         # digits with commas / decimals / spaces
          (?:million|thousand|k)?  # optional scale word (not interpreted yet)
        )
    """

    pattern = rf"""
        {number_like}
        \s*
        (?P<unit>{unit_regex})
    """

    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


# ------------------------------------------------------------
# Main extractor (Phase 1 minimal version)
# ------------------------------------------------------------

def extract_kpis_regex_v2(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:
    """
    Phase 1 version:
    - Simple number + unit matching
    - Does NOT interpret or convert numbers
    - Returns raw_value and raw_unit only
    - One hit per KPI (first match)
    - Uses universal_kpis.json ("units" only)

    Reliable for esg_report_v1 / v2 / v3.
    """
    results: Dict[str, Dict[str, Any]] = {}

    # Normalize whitespace so that regex is not confused by newlines
    cleaned = " ".join(text.split())

    for kpi_code, meta in kpi_schema.items():
        units = meta.get("units", [])
        if not units:
            logger.warning("v2 regex extractor: KPI '%s' has no units; skipping", kpi_code)
            continue

        pattern = _build_pattern_for_kpi(units)
        m = pattern.search(cleaned)

        if not m:
            continue

        raw_value = m.group("value").strip()
        raw_unit = m.group("unit").strip()

        logger.info(
            "v2 regex hit for %s: raw_value='%s', raw_unit='%s'",
            kpi_code, raw_value, raw_unit
        )

        results[kpi_code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "confidence": base_confidence,
        }

    return results

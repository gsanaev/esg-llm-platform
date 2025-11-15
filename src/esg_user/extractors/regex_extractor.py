from __future__ import annotations

import logging
import re
from typing import Dict, List, Any

from esg_system.config import load_config
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Number normalization
# -------------------------------------------------------------------


def normalize_number(raw: str, context: str) -> float | None:
    """
    Convert extracted raw number into float.

    Handles:
    - commas: "1,234.5" → 1234.5
    - spaces: "1 234" → 1234
    - parentheses: "(123)" → 123
    - 'million' / 'thousand' keywords in context to scale the value

    Parameters
    ----------
    raw : str
        Raw numeric string from regex capture.
    context : str
        Surrounding text used to detect scale modifiers like 'million' or 'thousand'.

    Returns
    -------
    float | None
        Parsed and scaled float, or None if parsing fails.
    """
    cleaned = (
        raw.replace(",", "")
           .replace(" ", "")
           .replace("(", "")
           .replace(")", "")
    )

    try:
        value = float(cleaned)
    except ValueError:
        logger.debug("normalize_number: failed to parse '%s'", raw)
        return None

    lower_context = context.lower()

    if "million" in lower_context:
        value *= 1_000_000
    elif "thousand" in lower_context:
        value *= 1_000

    return value


# -------------------------------------------------------------------
# Pattern building
# -------------------------------------------------------------------


def build_kpi_patterns(synonyms: List[str], units: List[str]) -> List[re.Pattern[str]]:
    """
    Build regex patterns that capture:
        - KPI synonym (literal string)
        - any text (non-greedy)
        - numeric value (group 1)
        - unit (group 2, one of allowed units)

    Parameters
    ----------
    synonyms : list[str]
        List of KPI name variants like ["total ghg emissions", "scope 1+2"]
    units : list[str]
        List of possible units like ["tCO2e", "ktCO2e"]

    Returns
    -------
    list[Pattern]
        Compiled regex patterns.
    """
    patterns: List[re.Pattern[str]] = []

    if not synonyms or not units:
        return patterns

    # units OR-group, escape special characters
    unit_regex = "|".join(re.escape(u) for u in units)

    # number pattern: captures things like:
    #  123
    #  1,234.56
    #  (1 234)
    number_pattern = r"(-?\(?\d[\d\s,\.]*\)?)"

    for synonym in synonyms:
        if not synonym:
            continue

        pattern_text = (
            rf"{re.escape(synonym)}"   # literal KPI synonym
            rf".*?"                    # any chars, non-greedy
            rf"{number_pattern}"       # capture group(1): numeric
            rf"\s*({unit_regex})"      # capture group(2): unit
        )

        try:
            compiled = re.compile(
                pattern_text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            patterns.append(compiled)
        except re.error as e:
            logger.warning(
                "Failed to compile regex for synonym '%s': %s",
                synonym,
                e,
            )

    return patterns


# -------------------------------------------------------------------
# Main extractor
# -------------------------------------------------------------------


def extract_kpis_regex(text: str) -> Dict[str, ExtractorResult]:
    """
    Regex-based KPI extraction.

    Strategy:
    - Use mapping_rules["universal_kpis"] to get synonyms and units for each KPI.
    - For each KPI, build a set of patterns.
    - Scan the full text, stop at the first match per KPI.
    - Normalize the extracted number using context.
    - Return a Dict[str, ExtractorResult].

    Returns
    -------
    Dict[str, ExtractorResult]
        Mapping KPI code → ExtractorResult(value, unit, confidence).
        Confidence is moderate (e.g. 0.6) since regex is naive.
    """
    cfg = load_config()
    universal_rules: Dict[str, Dict[str, Any]] = cfg.mapping_rules.get("universal_kpis", {})

    results: Dict[str, ExtractorResult] = {}

    logger.debug("Regex extractor: processing KPIs: %s", list(universal_rules.keys()))

    for kpi_code, kpi_info in universal_rules.items():
        synonyms: List[str] = kpi_info.get("synonyms", []) or []
        units: List[str] = kpi_info.get("units", []) or []

        logger.debug(
            "Regex extractor: KPI '%s' with synonyms=%s units=%s",
            kpi_code,
            synonyms,
            units,
        )

        patterns = build_kpi_patterns(synonyms, units)

        # If we cannot build patterns (no units, etc.), skip KPI
        if not patterns:
            logger.debug(
                "Regex extractor: no patterns built for KPI '%s' (missing synonyms/units).",
                kpi_code,
            )
            continue

        # Try each pattern until we get a match
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue

            raw_value = match.group(1)
            unit = match.group(2)

            context_span = text[max(0, match.start() - 80): match.end() + 80]

            value = normalize_number(raw_value, context_span)

            logger.info(
                "Regex extractor hit for %s: raw='%s' unit='%s' → value=%s",
                kpi_code,
                raw_value,
                unit,
                value,
            )

            results[kpi_code] = ExtractorResult(
                value=value,
                unit=unit,
                confidence=0.6,
            )

            # Stop after first successful match for this KPI
            break

    return results

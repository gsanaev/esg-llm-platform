import re
from typing import Dict, Any, List, Optional
from esg_system.config import load_config


# -----------------------------
# Helper functions
# -----------------------------

def normalize_number(s: str) -> Optional[float]:
    """Convert extracted numeric string into a float. Handles commas."""
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def build_kpi_patterns(synonyms: List[str]) -> List[re.Pattern]:
    """
    Build simple regex patterns to match KPI synonyms and capture nearby numbers.
    Pattern: synonym ... number
    """
    patterns = []
    for synonym in synonyms:
        pattern = re.compile(
            rf"{re.escape(synonym)}[^0-9]*([0-9][0-9,\.]*)",
            re.IGNORECASE
        )
        patterns.append(pattern)

    return patterns


def find_unit_around(text: str, number_span: tuple, allowed_units: List[str]) -> Optional[str]:
    """
    Look near the numeric match for allowed units.
    We scan a small window after the number.
    """
    _, end = number_span
    window = text[end : end + 20]  # search 20 chars after the number

    for unit in allowed_units:
        pattern = re.compile(rf"\b{re.escape(unit)}\b", re.IGNORECASE)
        if pattern.search(window):
            return unit

    return None


# -----------------------------
# Main extraction function
# -----------------------------

def extract_kpis_regex(text: str) -> Dict[str, Dict[str, Any]]:
    """Extract KPI values from text using simple regex patterns."""

    cfg = load_config()
    results = {}

    # Only universal KPIs for now (GRI/SASB come later)
    universal_rules = cfg.mapping_rules.get("universal_kpis", {})

    for kpi_code, kpi_info in universal_rules.items():
        synonyms = kpi_info.get("synonyms", [])
        allowed_units = kpi_info.get("units", [])
        patterns = build_kpi_patterns(synonyms)

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                value_raw = match.group(1)
                value = normalize_number(value_raw)

                # Find unit near the numeric value
                unit = find_unit_around(text, match.span(1), allowed_units)

                results[kpi_code] = {
                    "value": value,
                    "unit": unit
                }
                break  # Only first match per KPI needed

    return results

import re
from typing import Dict, Any, List
from esg_system.config import load_config


def normalize_number(raw: str, context: str) -> float | None:
    """
    Convert extracted raw number into float.
    Handle:
    - commas, spaces
    - parentheses
    - million / thousand scale words
    """

    cleaned = raw.replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("(", "").replace(")", "")

    try:
        value = float(cleaned)
    except ValueError:
        return None

    # scaling
    lower_context = context.lower()

    if "million" in lower_context:
        value *= 1_000_000
    elif "thousand" in lower_context:
        value *= 1_000

    return value


def build_kpi_patterns(synonyms: List[str], units: List[str]) -> List[re.Pattern]:
    """
    Match:
    synonym → any text → number → unit
    """

    patterns = []
    unit_regex = "|".join(re.escape(u) for u in units)

    # improved number pattern
    number_pattern = r"(-?\(?\d[\d\s,\.]*\)?)"

    for synonym in synonyms:
        pattern = re.compile(
            rf"{re.escape(synonym)}"
            rf".*?"                 # lazy text match
            rf"{number_pattern}"    # number
            rf"\s*(?:{unit_regex})",# valid unit
            re.IGNORECASE | re.DOTALL,
        )
        patterns.append(pattern)

    return patterns


def extract_kpis_regex(text: str) -> Dict[str, Dict[str, Any]]:
    cfg = load_config()
    results = {}

    universal_rules = cfg.mapping_rules.get("universal_kpis", {})

    for kpi_code, kpi_info in universal_rules.items():
        synonyms = kpi_info.get("synonyms", [])
        units = kpi_info.get("units", [])

        patterns = build_kpi_patterns(synonyms, units)

        for pattern in patterns:
            match = pattern.search(text)
            if match:
                raw_value = match.group(1)
                context_span = text[max(0, match.start() - 40): match.end() + 40]
                value = normalize_number(raw_value, context_span)

                results[kpi_code] = {
                    "value": value,
                    "unit": units[0] if units else None
                }
                break

    return results

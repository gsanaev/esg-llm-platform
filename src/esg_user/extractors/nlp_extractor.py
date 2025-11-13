import re
from typing import Dict, Any, List, Optional
from esg_system.config import load_config


# ---------------------------------------
# Helper functions
# ---------------------------------------

def split_sentences(text: str) -> List[str]:
    """
    Very simple sentence splitter.
    Splits on '.', '?', '!' while preserving readable chunks.
    """
    parts = re.split(r'(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def find_numbers(sentence: str) -> List[re.Match]:
    """
    Find all numeric values in the sentence.
    Returns regex match objects.
    """
    pattern = re.compile(r"\b[0-9][0-9,\.]*\b")
    return list(pattern.finditer(sentence))


def normalize_number(s: str) -> Optional[float]:
    """Convert extracted numeric string into a float. Handles commas."""
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def get_closest_number(sentence: str, synonym_match: re.Match, numbers: List[re.Match]) -> Optional[re.Match]:
    """
    Select the number closest to the synonym match position.
    """
    if not numbers:
        return None

    synonym_pos = synonym_match.start()
    distances = [(abs(n.start() - synonym_pos), n) for n in numbers]
    distances.sort(key=lambda x: x[0])

    return distances[0][1]  # return the match with the smallest distance


def find_unit_near(sentence: str, number_match: re.Match, allowed_units: List[str]) -> Optional[str]:
    """
    Look near the numeric match for allowed units inside the same sentence.
    """
    start, end = number_match.span()
    window = sentence[end : end + 20]  # scan 20 chars after the number

    for unit in allowed_units:
        pattern = re.compile(rf"\b{re.escape(unit)}\b", re.IGNORECASE)
        if pattern.search(window):
            return unit

    return None


# ---------------------------------------
# Main extraction function
# ---------------------------------------

def extract_kpis_nlp(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Minimal NLP-based KPI extraction.

    - split text into sentences
    - for each KPI synonym, find matching sentences
    - detect all numbers in the sentence
    - choose the number closest to the KPI synonym
    - detect unit near that number
    """
    cfg = load_config()
    results = {}

    universal_rules = cfg.mapping_rules.get("universal_kpis", {})

    sentences = split_sentences(text)

    for kpi_code, kpi_info in universal_rules.items():
        synonyms = kpi_info.get("synonyms", [])
        allowed_units = kpi_info.get("units", [])

        # Track best match for this KPI
        best_value = None
        best_unit = None

        for sentence in sentences:
            # Check each synonym
            for synonym in synonyms:
                synonym_pattern = re.compile(rf"\b{re.escape(synonym)}\b", re.IGNORECASE)
                syn_match = synonym_pattern.search(sentence)

                if not syn_match:
                    continue

                # Get all numbers in the sentence
                numbers = find_numbers(sentence)
                if not numbers:
                    continue

                # Choose the number closest to the synonym
                number_match = get_closest_number(sentence, syn_match, numbers)
                if not number_match:
                    continue

                value_raw = number_match.group()
                value = normalize_number(value_raw)

                # Look for the unit
                unit = find_unit_near(sentence, number_match, allowed_units)

                best_value = value
                best_unit = unit
                break  # stop checking other synonyms for this sentence

        # Save result if we found anything
        if best_value is not None:
            results[kpi_code] = {
                "value": best_value,
                "unit": best_unit
            }

    return results

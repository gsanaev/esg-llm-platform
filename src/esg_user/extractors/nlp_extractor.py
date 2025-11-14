import re
from typing import Dict, Any, List, Tuple
from esg_system.config import load_config


# -----------------------------
# Utility functions
# -----------------------------

def split_sentences(text: str) -> List[str]:
    """
    Lightweight rule-based sentence splitter.
    """
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def extract_numbers(text: str) -> List[Tuple[str, int]]:
    """
    Extract numeric expressions and return (number_str, char_position).
    """
    number_pattern = r"-?\(?\d[\d\s,\.]*\)?(?:\s*(?:million|thousand))?"
    results = []

    for match in re.finditer(number_pattern, text, flags=re.IGNORECASE):
        results.append((match.group(0), match.start()))

    return results


def normalize_number(raw: str) -> float | None:
    """
    Handle commas, parentheses, scaling words.
    """
    cleaned = raw.lower().strip()
    multiplier = 1

    if "million" in cleaned:
        multiplier = 1_000_000
        cleaned = cleaned.replace("million", "")
    elif "thousand" in cleaned:
        multiplier = 1_000
        cleaned = cleaned.replace("thousand", "")

    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("(", "").replace(")", "")

    try:
        return float(cleaned) * multiplier
    except ValueError:
        return None


def find_units(text: str, allowed_units: List[str]) -> str | None:
    for unit in allowed_units:
        pattern = re.compile(rf"\b{re.escape(unit)}\b", re.IGNORECASE)
        if pattern.search(text):
            return unit
    return None


# -----------------------------
# NLP KPI Extraction
# -----------------------------

def extract_kpis_nlp(text: str) -> Dict[str, Dict[str, Any]]:
    cfg = load_config()
    results = {}

    sentences = split_sentences(text)

    universal_rules = cfg.mapping_rules.get("universal_kpis", {})

    for kpi_code, kpi_info in universal_rules.items():
        synonyms = kpi_info.get("synonyms", [])
        allowed_units = kpi_info.get("units", [])

        best_score = -1
        best_value = None
        best_unit = None

        # Search each sentence
        for i, sent in enumerate(sentences):
            lower = sent.lower()

            # Check if sentence contains any synonym
            if not any(syn.lower() in lower for syn in synonyms):
                continue

            # Get context: previous, current, next sentence
            context = ""
            if i > 0:
                context += sentences[i - 1] + " "
            context += sentences[i] + " "
            if i < len(sentences) - 1:
                context += sentences[i + 1]

            # Extract numbers with positions
            numbers = extract_numbers(context)

            for raw_value, pos in numbers:
                value = normalize_number(raw_value)
                if value is None:
                    continue

                # Determine if unit exists in context
                unit = find_units(context, allowed_units)

                # Scoring
                # Higher score = better match
                score = 0
                if raw_value in sent:
                    score += 2
                if unit:
                    score += 1

                # Update best match
                if score > best_score:
                    best_score = score
                    best_value = value
                    best_unit = unit

        if best_value is not None:
            results[kpi_code] = {
                "value": best_value,
                "unit": best_unit if best_unit else allowed_units[0] if allowed_units else None
            }

    return results

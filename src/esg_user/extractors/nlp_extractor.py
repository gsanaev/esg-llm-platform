from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple, Optional, Any

from esg_system.config import load_config
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------

def split_sentences(text: str) -> List[str]:
    """
    Lightweight, robust sentence splitter.

    Replaces newlines with spaces, then splits on punctuation.
    Handles cases like:
    - "GHG emissions were 10 million tCO2e. Scope 2 was 5."
    - "Energy use reached 1,234,000 MWh (up 5%)."
    """
    text = text.replace("\n", " ")

    # Split on punctuation followed by whitespace
    parts = re.split(r"(?<=[\.\!\?])\s+", text)

    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------
# Number extraction
# ---------------------------------------------------------------------

NUMBER_REGEX = r"-?\(?\d[\d\s,\.]*\)?(?:\s*(?:million|thousand))?"

def extract_numbers(text: str) -> List[Tuple[str, int]]:
    """
    Extract numbers like:
    - 123
    - 1,234.56
    - (1 234)
    - 20 million
    - 100 thousand

    Returns list of (raw_number_string, start_position)
    """
    matches: List[Tuple[str, int]] = []

    for m in re.finditer(NUMBER_REGEX, text, flags=re.IGNORECASE):
        matches.append((m.group(0), m.start()))

    return matches


def normalize_number(raw: str) -> Optional[float]:
    """
    Convert number string into float.

    Handles:
    - parentheses for negatives or formatting
    - million / thousand modifiers
    - commas, spaces

    Returns None if parsing fails.
    """
    cleaned = raw.lower().strip()
    multiplier = 1.0

    if "million" in cleaned:
        multiplier = 1_000_000.0
        cleaned = cleaned.replace("million", "")
    elif "thousand" in cleaned:
        multiplier = 1_000.0
        cleaned = cleaned.replace("thousand", "")

    cleaned = cleaned.replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("(", "").replace(")", "")

    try:
        return float(cleaned) * multiplier
    except Exception:
        return None


# ---------------------------------------------------------------------
# Unit detection
# ---------------------------------------------------------------------

def find_units(text: str, allowed_units: List[str]) -> Optional[str]:
    """
    Look for exact unit matches within a given text block.

    Case-insensitive.
    """
    for unit in allowed_units:
        if re.search(rf"\b{re.escape(unit)}\b", text, flags=re.IGNORECASE):
            return unit
    return None


# ---------------------------------------------------------------------
# Synonym matching
# ---------------------------------------------------------------------

def sentence_matches_synonyms(sentence: str, synonyms: List[str]) -> bool:
    """
    Check whether any KPI synonym appears in the sentence.

    Two checks:
    - substring match
    - token-based contains match (more robust)
    """
    s_lower = sentence.lower()

    for syn in synonyms:
        syn_lower = syn.lower()

        # Direct substring match
        if syn_lower in s_lower:
            return True

        # Tokenized match (e.g., "ghg emissions" in "total ghg company emissions")
        syn_tokens = syn_lower.split()
        if all(tok in s_lower for tok in syn_tokens):
            return True

    return False


# ---------------------------------------------------------------------
# Main NLP extractor
# ---------------------------------------------------------------------

def extract_kpis_nlp(text: str) -> Dict[str, ExtractorResult]:
    """
    Heuristic NLP-based KPI extractor.

    Steps:
    1. Split the document into sentences.
    2. For each KPI:
       - find sentences containing synonyms
       - build a context window (prev + current + next)
       - extract candidate numbers
       - detect units in context
       - score candidates
    3. Return highest-scoring result per KPI.

    Returns:
        Dict[str, ExtractorResult]
    """
    cfg = load_config()
    rules: Dict[str, Dict[str, Any]] = cfg.mapping_rules.get("universal_kpis", {})

    results: Dict[str, ExtractorResult] = {}

    sentences = split_sentences(text)

    logger.debug("NLP extractor: %d sentences detected", len(sentences))
    logger.debug("NLP extractor KPIs: %s", list(rules.keys()))

    for kpi_code, kpi_info in rules.items():
        synonyms: List[str] = kpi_info.get("synonyms", []) or []
        allowed_units: List[str] = kpi_info.get("units", []) or []

        logger.debug(
            "Processing KPI '%s' with synonyms=%s units=%s",
            kpi_code, synonyms, allowed_units
        )

        best_score = -1
        best_value: Optional[float] = None
        best_unit: Optional[str] = None

        for i, sentence in enumerate(sentences):

            # Step 1: Check if sentence contains synonyms
            if not sentence_matches_synonyms(sentence, synonyms):
                continue

            # Step 2: Build context window
            context = ""
            if i > 0:
                context += sentences[i - 1] + " "
            context += sentence + " "
            if i < len(sentences) - 1:
                context += sentences[i + 1]

            # Step 3: Extract numeric candidates
            candidates = extract_numbers(context)

            for raw_num, _ in candidates:
                value = normalize_number(raw_num)
                if value is None:
                    continue

                unit = find_units(context, allowed_units)

                # Heuristic scoring:
                # - Raw number appears inside the main sentence → +2
                # - Unit found → +1
                score = 0
                if raw_num in sentence:
                    score += 2
                if unit:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_value = value
                    best_unit = unit

        # Finalize
        if best_value is not None:
            logger.info(
                "NLP extractor hit for %s: value=%s unit=%s score=%s",
                kpi_code, best_value, best_unit, best_score
            )

            results[kpi_code] = ExtractorResult(
                value=best_value,
                unit=best_unit,
                confidence=0.65,  # moderate confidence
            )

    return results

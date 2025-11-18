# src/esg_v2/extractors/nlp_extractor_v2.py
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


# ============================================================
# Small helpers
# ============================================================

def _split_into_sentences(text: str) -> list[str]:
    """
    Very simple sentence splitter:
    - splits on '.', '!', '?', and newlines
    - collapses whitespace in each sentence
    """
    # First normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Split on punctuation that typically ends sentences
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [c.strip() for c in chunks if c.strip()]


def _build_kpi_synonyms(kpi_schema: Mapping[str, Any]) -> Dict[str, list[str]]:
    """
    Build lowercase synonym list per KPI.
    Falls back to code-based phrase if no synonyms are provided.
    """
    syns: Dict[str, list[str]] = {}
    for code, meta in kpi_schema.items():
        raw_syns = meta.get("synonyms") or [code.replace("_", " ")]
        syns[code] = [s.lower() for s in raw_syns]
    return syns


def _build_kpi_units(kpi_schema: Mapping[str, Any]) -> Dict[str, list[str]]:
    """Return raw units (as-is) per KPI."""
    return {code: (meta.get("units") or []) for code, meta in kpi_schema.items()}


# ============================================================
# Regex pattern builder (cached)
# ============================================================

@lru_cache(maxsize=256)
def _build_pattern_for_units(units_key: str) -> re.Pattern:
    """
    Create a number + unit regex for a given set of units.
    We cache by a joined 'units_key' to avoid recompiling.
    """
    units = units_key.split("||")
    unit_regex = "|".join(re.escape(u) for u in units)

    number_like = r"""
        (?P<value>
            [0-9][0-9,\.\s]*        # digits with grouping/decimals
            (?:million|thousand|k)? # optional scale word
        )
    """

    pattern = rf"""
        {number_like}
        \s*
        (?P<unit>{unit_regex})
    """

    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


def _get_pattern_for_units(units: list[str]) -> re.Pattern:
    """
    Public interface to the cached pattern builder.
    If units is empty, this function should not be called.
    """
    units_key = "||".join(units)
    return _build_pattern_for_units(units_key)


# ============================================================
# Main NLP extractor
# ============================================================

def extract_kpis_nlp_v2(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.65,
) -> Dict[str, Dict[str, Any]]:
    """
    NLP-style extractor (v2):

    - Works on plain text, not tables.
    - Uses KPI synonyms to find a 'sentence window' relevant to each KPI.
    - Inside that window, searches for <number + unit> tailored to that KPI's units.
    - Returns raw_value, raw_unit, confidence in the SAME SHAPE as regex_extractor_v2.

    This is designed to pair with normalize_regex_result_v2.
    """

    sentences = _split_into_sentences(text)
    if not sentences:
        return {}

    lowered_sentences = [s.lower() for s in sentences]

    kpi_syns = _build_kpi_synonyms(kpi_schema)
    kpi_units = _build_kpi_units(kpi_schema)

    results: Dict[str, Dict[str, Any]] = {}

    # For each KPI, scan sentences for a synonym and then search
    # a local window (sentence i and i+1) for number+unit.
    for code, meta in kpi_schema.items():
        if code in results:
            continue

        units = kpi_units.get(code, [])
        if not units:
            # No units defined → skip (this extractor is unit-dependent)
            continue

        synonyms = kpi_syns.get(code, [])
        if not synonyms:
            continue

        pattern = _get_pattern_for_units(units)

        for idx, sent_lower in enumerate(lowered_sentences):
            # Check if this sentence mentions the KPI (by synonym)
            if not any(syn in sent_lower for syn in synonyms):
                continue

            # Build a small context window: current + next sentence
            window = sentences[idx]
            if idx + 1 < len(sentences):
                window = window + " " + sentences[idx + 1]

            window = re.sub(r"\s+", " ", window)

            m = pattern.search(window)
            if not m:
                continue

            raw_value = m.group("value").strip()
            raw_unit = m.group("unit").strip()

            logger.info(
                "nlp_v2 hit %s: raw_value='%s', raw_unit='%s'",
                code, raw_value, raw_unit
            )

            results[code] = {
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "confidence": base_confidence,
            }

            # FIRST-HIT rule: stop after first match for this KPI
            break

    return results

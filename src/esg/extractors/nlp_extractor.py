# src/esg/extractors/nlp_extractor.py
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any, Dict, Mapping

logger = logging.getLogger(__name__)


# ======================================================================
# Sentence Splitting
# ======================================================================

def _split_into_sentences(text: str) -> list[str]:
    """
    Very small heuristic sentence splitter:
      - Normalize whitespace
      - Split on '.', '!', '?', and newlines
      - Drop empty fragments
    """
    text = re.sub(r"\s+", " ", text)
    chunks = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [c.strip() for c in chunks if c.strip()]


# ======================================================================
# KPI Synonyms & Units
# ======================================================================

def _build_kpi_synonyms(kpi_schema: Mapping[str, Any]) -> Dict[str, list[str]]:
    """
    Build lowercase synonyms per KPI.
    Fallback = code.replace('_',' ') if schema provides no synonyms.
    """
    syns: Dict[str, list[str]] = {}
    for code, meta in kpi_schema.items():
        raw = meta.get("synonyms") or [code.replace("_", " ")]
        syns[code] = [s.lower() for s in raw]
    return syns


def _build_kpi_units(kpi_schema: Mapping[str, Any]) -> Dict[str, list[str]]:
    """Extract units (as-is) per KPI from schema."""
    return {code: (meta.get("units") or []) for code, meta in kpi_schema.items()}


# ======================================================================
# Cached Regex Pattern Builder
# ======================================================================

@lru_cache(maxsize=256)
def _build_pattern_for_units(units_key: str) -> re.Pattern:
    """
    Construct a `<number><unit>` regex for a given set of units.
    Cached so multiple KPIs with same unit set don’t recompile repeatedly.
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
    """Return cached regex pattern for units list."""
    return _build_pattern_for_units("||".join(units))


# ======================================================================
# Main NLP Extractor
# ======================================================================

def extract_kpis_nlp(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.40,   # LOWER NLP confidence
) -> Dict[str, Dict[str, Any]]:
    """
    Lightweight NLP extractor that:
      1. Splits text into sentences.
      2. Finds sentences mentioning the KPI via synonyms.
      3. Searches within a small window (sentence + next)
         for a `<number> <unit>` match.
      4. Returns raw_value, raw_unit, and confidence.

    NLP is intentionally weak and conservative.
    """
    sentences = _split_into_sentences(text)
    if not sentences:
        return {}

    lowered = [s.lower() for s in sentences]

    kpi_syns = _build_kpi_synonyms(kpi_schema)
    kpi_units = _build_kpi_units(kpi_schema)

    results: Dict[str, Dict[str, Any]] = {}

    for code in kpi_schema:
        if code in results:
            continue

        units = kpi_units.get(code, [])
        if not units:
            continue

        synonyms = kpi_syns.get(code, [])
        if not synonyms:
            continue

        # Pattern A: <value><unit>
        pattern_with_unit = _get_pattern_for_units(units)

        # Pattern B: value only (very weak)
        pattern_value_only = re.compile(
            r"(?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)",
            re.IGNORECASE,
        )

        # Scan sentences
        for i, sent_lower in enumerate(lowered):
            if not any(syn in sent_lower for syn in synonyms):
                continue

            # Window: current + next sentence
            window = sentences[i]
            if i + 1 < len(sentences):
                window += " " + sentences[i + 1]

            window = re.sub(r"\s+", " ", window)

            # Normalize PDF weird spaces (NBSP and similar)
            window = window.replace("\u00A0", " ")
            window = window.replace("\u202F", " ")
            window = window.replace("\u2007", " ")
            window = window.replace("\u2060", " ")

            # ---------- STRONG MATCH: value+unit ----------
            m = pattern_with_unit.search(window)
            if m:
                raw_value = m.group("value").strip()
                raw_unit = m.group("unit").strip()

                logger.info(
                    "nlp hit %s (with unit): raw_value='%s', raw_unit='%s'",
                    code, raw_value, raw_unit
                )

                results[code] = {
                    "raw_value": raw_value,
                    "raw_unit": raw_unit,
                    "confidence": base_confidence + 0.15,  # boost strong match
                }
                break

            # ---------- WEAK MATCH: value only ----------
            # Only allow weak match if the window contains at least one expected unit
            # (prevent matching the first KPI number in unrelated context sentences)
            if not any(u.lower() in window.lower() for u in units):
                continue

            m2 = pattern_value_only.search(window)
            if not m2:
                continue

            raw_value = m2.group("value").strip()

            # ---- Reject junk patterns ----

            # Reject values ending with a comma: "500,000,"
            if raw_value.endswith(","):
                continue

            # Reject years
            try:
                v = float(raw_value.replace(",", ""))
                if 1000 <= v <= 2100:
                    continue
            except Exception:
                pass

            # Reject tiny numbers (< 100)
            try:
                v = float(raw_value.replace(",", ""))
                if v < 100:
                    continue
            except Exception:
                pass

            logger.info(
                "nlp hit %s (value only): raw_value='%s'",
                code, raw_value
            )

            results[code] = {
                "raw_value": raw_value,
                "raw_unit": None,
                "confidence": base_confidence,  # very weak match
            }
            break

    return results

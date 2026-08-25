# src/esg/extractors/regex_extractor.py
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Dict, Any, Mapping

from esg.core.schema import get_accepted_units, get_synonyms

logger = logging.getLogger(__name__)


# =====================================================================
# Cached regex builder (value-first)
# =====================================================================

@lru_cache(maxsize=256)
def _pattern_value_first(units_key: str) -> re.Pattern:
    units = [u for u in units_key.split("||") if u]
    if not units:
        return re.compile(r"(?!x)x")

    unit_regex = "|".join(re.escape(u) for u in units)

    pattern = rf"""
        (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        \s*
        (?P<unit>{unit_regex})
    """
    return re.compile(pattern, re.IGNORECASE | re.VERBOSE)


# =====================================================================
# Pattern B: "(unit) value"
# =====================================================================

def _pattern_paren_unit_first(units: list[str]) -> re.Pattern:
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""\(
                (?P<unit>{unit_regex})
            \)
            \s*(?:of|is|=|:)?\s*
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        """,
        re.IGNORECASE | re.VERBOSE
    )


# =====================================================================
# Pattern C: "unit value" (NO parentheses)
# =====================================================================

def _pattern_unit_first(units: list[str]) -> re.Pattern:
    """
    Matches: "tCO2e 123,400" but avoids matching inside e.g. "(tCO2e)"
    """
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""
            (?<!\()                      # cannot be inside parentheses
            (?P<unit>{unit_regex})
            \s*
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
        """,
        re.IGNORECASE | re.VERBOSE
    )

# =====================================================================
# Pattern D: "(unit) ... value" within max window (120 chars)
# =====================================================================

def _pattern_paren_unit_near_value(units: list[str], max_window: int = 120) -> re.Pattern:
    """
    Matches cases like:
        "(tCO2e) ... was 123,400"
        "(MWh) ... amounted to 500,000,"
        "(m3) ... is around 1,200,000."
    where the distance between ')' and the value is <= max_window characters.

    Trailing punctuation after the value is allowed.
    """
    unit_regex = "|".join(re.escape(u) for u in units)

    return re.compile(
        rf"""
            \(
                (?P<unit>{unit_regex})
            \)
            (?P<middle>.{{0,{max_window}}}?)        # up to 120 chars
            (?P<value>[0-9][0-9,\.\s]*(?:million|thousand|k)?)
            \s*[,;.]?                                # optional trailing punctuation
        """,
        re.IGNORECASE | re.VERBOSE
    )


# =====================================================================
# Public getter for pattern A
# =====================================================================

def _get_pattern_value_first(units: list[str]) -> re.Pattern:
    return _pattern_value_first("||".join(units))


def _norm_unit_identity(unit: str) -> str:
    """
    Normalize a unit token for detecting whether KPIs share units.
    """
    return "".join(unit.split()).lower().replace("³", "3")


def _has_shared_units(
    code: str,
    units: list[str],
    kpi_schema: Mapping[str, Any],
) -> bool:
    """
    Return True when another KPI accepts at least one equivalent unit.
    """
    own_units = {
        _norm_unit_identity(unit)
        for unit in units
    }

    for other_code, other_meta in kpi_schema.items():
        if other_code == code:
            continue

        other_units = {
            _norm_unit_identity(unit)
            for unit in get_accepted_units(other_meta)
        }

        if own_units & other_units:
            return True

    return False


def _nearest_metric_before(
    text: str,
    position: int,
    kpi_schema: Mapping[str, Any],
    *,
    max_distance: int = 120,
) -> str | None:
    """
    Return the KPI whose synonym occurs nearest before a regex match.

    Only synonyms within max_distance characters of the match are
    considered, preventing stale metric mentions from claiming a
    later value that happens to use the same unit.
    """
    lowered = text.lower()

    nearest_code: str | None = None
    nearest_position = -1

    for other_code, other_meta in kpi_schema.items():
        for synonym in get_synonyms(other_code, other_meta):
            synonym_lower = synonym.lower()

            synonym_position = lowered.rfind(
                synonym_lower,
                0,
                position,
            )

            if synonym_position < 0:
                continue

            synonym_end = synonym_position + len(synonym_lower)
            distance = position - synonym_end

            if distance > max_distance:
                continue

            if synonym_position > nearest_position:
                nearest_position = synonym_position
                nearest_code = other_code

    return nearest_code


def _first_semantic_match(
    pattern: re.Pattern,
    text: str,
    code: str,
    kpi_schema: Mapping[str, Any],
    *,
    require_metric_owner: bool,
) -> re.Match[str] | None:
    """
    Return the first match belonging to the requested KPI.

    Semantic ownership is required only for KPIs that share units with
    another KPI. Unique-unit KPIs preserve the existing regex behavior.
    """
    for match in pattern.finditer(text):
        if not require_metric_owner:
            return match

        if (
            _nearest_metric_before(
                text,
                match.start(),
                kpi_schema,
            )
            == code
        ):
            return match

    return None


# =====================================================================
# Main extractor
# =====================================================================

def extract_kpis_regex(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, Dict[str, Any]]:

    results: Dict[str, Dict[str, Any]] = {}
    if not text:
        return results

    cleaned = re.sub(r"\s+", " ", text)

    for code, meta in kpi_schema.items():
        units = get_accepted_units(meta)
        if not units:
            continue

        require_metric_owner = (
            bool(meta.get("requires_metric_context", False))
            or _has_shared_units(
                code,
                units,
                kpi_schema,
            )
        )

        # Build 3 patterns
        pA = _get_pattern_value_first(units)
        pB = _pattern_paren_unit_first(units)
        pC = _pattern_unit_first(units)

        # Try A: "<value> <unit>"
        mA = _first_semantic_match(
            pA,
            cleaned,
            code,
            kpi_schema,
            require_metric_owner=require_metric_owner,
        )
        if mA:
            v = mA.group("value").strip()
            u = mA.group("unit").strip()
            logger.info("regex hit %s (A value-unit): %s %s", code, v, u)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue

        # Try B: "(<unit>) <value>"
        mB = _first_semantic_match(
            pB,
            cleaned,
            code,
            kpi_schema,
            require_metric_owner=require_metric_owner,
        )
        if mB:
            v = mB.group("value").strip()
            u = mB.group("unit").strip()
            logger.info("regex hit %s (B paren-unit-value): (%s) %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue

        # Try C: "<unit> <value>" (no parentheses)
        mC = _first_semantic_match(
            pC,
            cleaned,
            code,
            kpi_schema,
            require_metric_owner=require_metric_owner,
        )
        if mC:
            v = mC.group("value").strip()
            u = mC.group("unit").strip()
            logger.info("regex hit %s (C unit-value): %s %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue


        # Try D: "(<unit>) ... <value>" (window-limited)
        pD = _pattern_paren_unit_near_value(units, max_window=120)
        mD = _first_semantic_match(
            pD,
            cleaned,
            code,
            kpi_schema,
            require_metric_owner=require_metric_owner,
        )
        if mD:
            v = mD.group("value").strip().rstrip(".,;")
            u = mD.group("unit").strip()
            logger.info("regex hit %s (D paren-unit-near-value): (%s) ... %s", code, u, v)
            results[code] = {"raw_value": v, "raw_unit": u, "confidence": base_confidence}
            continue


    return results


def extract_kpi_candidates_regex(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    base_confidence: float = 0.6,
) -> Dict[str, list[Dict[str, Any]]]:
    """
    Extract all non-overlapping regex observations for each KPI.

    Pattern priority remains A -> B -> C -> D when overlapping matches
    represent the same text span. The legacy extract_kpis_regex() API
    remains unchanged.
    """
    results: Dict[str, list[Dict[str, Any]]] = {}
    if not text:
        return results

    cleaned = re.sub(r"\s+", " ", text)

    for code, meta in kpi_schema.items():
        units = get_accepted_units(meta)
        if not units:
            continue

        require_metric_owner = (
            bool(meta.get("requires_metric_context", False))
            or _has_shared_units(
                code,
                units,
                kpi_schema,
            )
        )

        patterns = [
            ("A", _get_pattern_value_first(units)),
            ("B", _pattern_paren_unit_first(units)),
            ("C", _pattern_unit_first(units)),
            (
                "D",
                _pattern_paren_unit_near_value(
                    units,
                    max_window=120,
                ),
            ),
        ]

        accepted_spans: list[tuple[int, int]] = []
        candidates: list[tuple[int, Dict[str, Any]]] = []

        for pattern_name, pattern in patterns:
            for match in pattern.finditer(cleaned):
                start, end = match.span()

                if require_metric_owner:
                    owner = _nearest_metric_before(
                        cleaned,
                        start,
                        kpi_schema,
                    )

                    if owner != code:
                        continue

                overlaps_existing = any(
                    start < existing_end and end > existing_start
                    for existing_start, existing_end in accepted_spans
                )
                if overlaps_existing:
                    continue

                raw_value = match.group("value").strip().rstrip(".,;")
                raw_unit = match.group("unit").strip()

                accepted_spans.append((start, end))
                candidates.append(
                    (
                        start,
                        {
                            "raw_value": raw_value,
                            "raw_unit": raw_unit,
                            "confidence": base_confidence,
                        },
                    )
                )

        if candidates:
            candidates.sort(key=lambda item: item[0])
            results[code] = [
                entry
                for _, entry in candidates
            ]

    return results

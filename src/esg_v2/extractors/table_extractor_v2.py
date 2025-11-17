# src/esg_v2/extractors/table_extractor_v2.py
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Mapping, List

import pdfplumber

logger = logging.getLogger(__name__)


def _normalize_unit_token(u: str) -> str:
    """
    Normalize unit strings for comparison:
    - lowercase
    - remove spaces
    - 'm³' -> 'm3'
    """
    return (
        u.lower()
        .replace(" ", "")
        .replace("³", "3")
    )


def _build_kpi_synonyms(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """
    Build a lowercase synonym list per KPI from the schema.
    Falls back to a simple name-based synonym if none are provided.
    """
    kpi_syns: Dict[str, List[str]] = {}

    for code, meta in kpi_schema.items():
        syns = meta.get("synonyms") or []
        # Fallback: use code name as a loose synonym
        if not syns:
            syns = [code.replace("_", " ")]
        kpi_syns[code] = [s.lower() for s in syns]

    return kpi_syns


def _build_kpi_units(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """
    Build normalized unit lists per KPI from the schema.
    """
    kpi_units: Dict[str, List[str]] = {}
    for code, meta in kpi_schema.items():
        raw_units = meta.get("units") or []
        kpi_units[code] = raw_units
    return kpi_units


def _parse_table_like_text(
    text: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Improved table-line parser:
    - Rejects narrative sentences
    - Requires table-like structure
    - Extracts last numeric token before a unit or at end
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return {}

    kpi_syns = _build_kpi_synonyms(kpi_schema)
    kpi_units = _build_kpi_units(kpi_schema)

    results: Dict[str, Dict[str, Any]] = {}

    # Words that should NEVER appear in table lines
    narrative_verbs = r"\b(reached|was|is|were|increased|decreased|reported|announced|grew|rose|fell)\b"

    for line in lines:
        lowered_line = line.lower()
        compact_line = lowered_line.replace(" ", "")

        # ------------------------------------------------------------
        # 1) Narrative filtering → reject full sentences
        # ------------------------------------------------------------
        if re.search(narrative_verbs, lowered_line):
            continue

        # ------------------------------------------------------------
        # 2) Require a table-like structure (at least ONE must match)
        # ------------------------------------------------------------
        table_like = False

        if "|" in line:
            table_like = True
        elif re.search(r"\s{2,}", line):       # multiple spaces used as columns
            table_like = True
        elif "(" in line and ")" in line:      # unit in parentheses
            table_like = True

        if not table_like:
            continue

        # ------------------------------------------------------------
        # 3) Match KPI synonyms
        # ------------------------------------------------------------
        for kpi_code, syns in kpi_syns.items():
            if kpi_code in results:
                continue

            if not any(s in lowered_line for s in syns):
                continue

            units_for_kpi = kpi_units.get(kpi_code, [])
            raw_unit: str | None = None

            # (a) Unit inside parentheses
            paren_match = re.search(r"\(([^)]+)\)", line)
            if paren_match:
                inside = paren_match.group(1).strip()
                inside_norm = _normalize_unit_token(inside)
                for u in units_for_kpi:
                    if inside_norm == _normalize_unit_token(u):
                        raw_unit = u
                        break
                if raw_unit is None:
                    raw_unit = inside

            # (b) Unit appearance anywhere
            if raw_unit is None:
                for u in units_for_kpi:
                    if _normalize_unit_token(u) in compact_line:
                        raw_unit = u
                        break

            # ------------------------------------------------------------
            # 4) Extract final numeric token (only if line looks like table)
            # ------------------------------------------------------------
            num_match = re.search(r"(-?\d[\d,\.\s]*)\s*$", line)
            if not num_match:
                continue

            raw_value = num_match.group(1).strip()

            logger.info(
                "table_v2 (text-mode) hit for %s: raw_value='%s', raw_unit='%s', line='%s'",
                kpi_code,
                raw_value,
                raw_unit,
                line,
            )

            results[kpi_code] = {
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "confidence": 0.85,
            }

    return results


def extract_kpis_from_tables_v2(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    v2 'table' extractor (Phase 1: text-mode only).

    For now this does NOT attempt grid-based table detection.
    It simply:
      - extracts all text from the PDF with pdfplumber
      - runs a line-based parser that looks for KPI synonyms + units
        in table-like lines
    This is intentionally simple and robust enough to handle
    `test_table_esg.pdf` and similar synthetic cases.

    Returns a sparse dict: only KPIs with hits are present.
    """
    logger.info("table_v2: extracting tables/lines from %s", pdf_path)

    # Extract raw text using pdfplumber (page by page)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts: List[str] = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
    except Exception as exc:
        logger.warning(
            "table_v2: failed to read '%s' via pdfplumber: %s", pdf_path, exc
        )
        return {}

    full_text = "\n".join(text_parts)
    if not full_text.strip():
        return {}

    # Parse table-like lines
    results = _parse_table_like_text(full_text, kpi_schema)

    # If nothing detected, return empty dict (no table hits)
    if not results:
        logger.info("table_v2: no table-like lines matched any KPI in %s", pdf_path)
    return results

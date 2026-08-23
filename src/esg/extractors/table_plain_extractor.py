# src/esg/extractors/table_plain_extractor.py
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Mapping, List

import pdfplumber

from esg.core.schema import get_accepted_units, get_synonyms

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _normalize_unit_token(u: str) -> str:
    """
    Normalize a unit token to improve substring matching inside lines.
    We remove spaces and unify '³' → '3' because PDFs often normalize this.
    """
    return (
        u.lower()
         .replace(" ", "")
         .replace("³", "3")
    )


def _is_table_plain_like(line: str) -> bool:
    """
    Lightweight heuristic to detect "row-like" table lines.
    Not strict; only tries to separate structured rows from narrative text.

    Triggers if:
      - multiple spaces (column-like)
      - explicit '|' separator
      - parentheses (often used for units or column headers)
    """
    return (
        "|" in line
        or re.search(r"\s{2,}", line)
        or ("(" in line and ")" in line)
    )


# ============================================================
# Core line parser
# ============================================================

def _parse_table_plain_candidates(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    page_number: int | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse extracted plaintext tables and detect KPI rows using:
      - KPI synonyms
      - Unit tokens (normalized)
      - Trailing-number heuristic

    Returns:
      { kpi_code: [{ raw_value, raw_unit, confidence, ... }, ...] }
    """
    # Clean and split lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {}

    # Precompute normalized synonyms per KPI
    syns_by_kpi: Dict[str, List[str]] = {
        code: [s.lower() for s in get_synonyms(code, meta)]
        for code, meta in kpi_schema.items()
    }

    # Units per KPI
    units_by_kpi: Dict[str, List[str]] = {
        code: get_accepted_units(meta)
        for code, meta in kpi_schema.items()
    }

    # Match a number at end of line
    number_pattern = re.compile(r"(-?\d[\d,.\s]*)\s*$")

    results: Dict[str, List[Dict[str, Any]]] = {}

    for line in lines:
        lowered = line.lower()

        # Skip narrative sentences (very small filter, safe)
        if re.search(r"\b(reported|announced|increased|decreased|reached)\b", lowered):
            continue

        # Line must be table-like
        if not _is_table_plain_like(line):
            continue

        # Try each KPI
        for code, syns in syns_by_kpi.items():

            # Synonym detection
            if not any(s in lowered for s in syns):
                continue

            # Unit detection via normalized substring match
            raw_unit = None
            compact = lowered.replace(" ", "")
            for u in units_by_kpi[code]:
                if _normalize_unit_token(u) in compact:
                    raw_unit = u
                    break

            # Number at end of line
            m = number_pattern.search(line)
            if not m:
                continue

            raw_value = m.group(1).strip()

            results.setdefault(code, []).append(
                {
                    "raw_value": raw_value,
                    "raw_unit": raw_unit,
                    "confidence": 0.85,
                    "page": page_number,
                    "source_context": line,
                }
            )

            logger.info(
                "table_plain hit %s: %s %s (line=%r)",
                code, raw_value, raw_unit, line
            )

    return results


def _parse_table_plain_text(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    page_number: int | None = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Compatibility parser returning one observation per KPI.

    Preserve the legacy behavior where the first matching line on a page wins.
    """
    candidates = _parse_table_plain_candidates(
        text,
        kpi_schema,
        page_number=page_number,
    )

    return {
        code: entries[0]
        for code, entries in candidates.items()
        if entries
    }


def extract_kpi_candidates_tables_plain(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract all plaintext-table observations for each KPI.

    Unlike the compatibility API, this function preserves repeated
    observations across lines and pages for later reconciliation.
    """
    logger.info("table_plain: extracting all candidates from %s", pdf_path)

    if not isinstance(pdf_path, str) or not os.path.isfile(pdf_path):
        return {}

    aggregated: Dict[str, List[Dict[str, Any]]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""

                if not page_text.strip():
                    continue

                hits = _parse_table_plain_candidates(
                    page_text,
                    kpi_schema,
                    page_number=page_number,
                )

                for code, entries in hits.items():
                    aggregated.setdefault(code, []).extend(entries)

    except Exception as exc:
        logger.warning(
            "table_plain: pdfplumber failed for %s: %s",
            pdf_path,
            exc,
        )
        return {}

    return aggregated


# ============================================================
# Public API
# ============================================================

def extract_kpis_tables_plain(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Extract KPI rows from tables using pdfplumber plaintext extraction.
    This is a lightweight parser — v3 is preferred for structured grids.

    Returns:
      { kpi_code: { raw_value, raw_unit, confidence } }
    """
    logger.info("table_plain: extracting from %s", pdf_path)

    # Defensive: ensure we were passed a file path
    if not isinstance(pdf_path, str) or not os.path.isfile(pdf_path):
        return {}

    # Try to extract plain text from all PDF pages
    aggregated: Dict[str, Dict[str, Any]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""

                if not page_text.strip():
                    continue

                hits = _parse_table_plain_text(
                    page_text,
                    kpi_schema,
                    page_number=page_number,
                )

                # Preserve existing first-hit behavior across the document
                for code, entry in hits.items():
                    if code not in aggregated:
                        aggregated[code] = entry

    except Exception as exc:
        logger.warning(
            "table_plain: pdfplumber failed for %s: %s",
            pdf_path,
            exc,
        )
        return {}

    return aggregated

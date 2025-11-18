# src/esg_v2/extractors/table_extractor_v2.py
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Mapping, List

import pdfplumber

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _normalize_unit_token(u: str) -> str:
    """Normalize unit for matching inside lines."""
    return u.lower().replace(" ", "").replace("³", "3")


def _is_table_like(line: str) -> bool:
    """
    Minimal table-structure heuristic:
      - multiple spaces → column-like
      - '|' separator
      - parentheses (often unit columns)
    """
    return (
        "|" in line
        or re.search(r"\s{2,}", line)
        or ("(" in line and ")" in line)
    )


# ============================================================
# Core line parser
# ============================================================

def _parse_table_text(
    text: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {}

    # Normalized synonyms
    syns_by_kpi: Dict[str, List[str]] = {
        code: [s.lower() for s in (meta.get("synonyms") or [code.replace("_", " ")])]
        for code, meta in kpi_schema.items()
    }

    # Units per KPI
    units_by_kpi: Dict[str, List[str]] = {
        code: (meta.get("units") or [])
        for code, meta in kpi_schema.items()
    }

    # Trailing-number pattern
    number_pattern = re.compile(r"(-?\d[\d,.\s]*)\s*$")

    results: Dict[str, Dict[str, Any]] = {}

    for line in lines:
        lowered = line.lower()

        # Skip very narrative lines
        if re.search(r"\b(reached|reported|announced|increased|decreased)\b", lowered):
            continue

        if not _is_table_like(line):
            continue

        for code, syns in syns_by_kpi.items():
            if code in results:
                continue

            # KPI label detection
            if not any(s in lowered for s in syns):
                continue

            # Detect unit by exact token presence
            raw_unit = None
            compact = lowered.replace(" ", "")
            for u in units_by_kpi[code]:
                if _normalize_unit_token(u) in compact:
                    raw_unit = u
                    break

            # Trailing number
            m = number_pattern.search(line)
            if not m:
                continue

            raw_value = m.group(1).strip()

            results[code] = {
                "raw_value": raw_value,
                "raw_unit": raw_unit,
                "confidence": 0.85,
            }

            logger.info(
                "table_v2 hit %s: %s %s (line=%r)",
                code, raw_value, raw_unit, line
            )

    return results


# ============================================================
# Public API
# ============================================================

def extract_kpis_from_tables_v2(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:

    logger.info("table_v2: extracting from %s", pdf_path)

    # Reject wrong inputs (e.g., full text passed accidentally)
    if not isinstance(pdf_path, str) or not os.path.isfile(pdf_path):
        return {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        logger.warning("table_v2: pdfplumber failed for %s: %s", pdf_path, exc)
        return {}

    full_text = "\n".join(pages).strip()
    if not full_text:
        return {}

    return _parse_table_text(full_text, kpi_schema)

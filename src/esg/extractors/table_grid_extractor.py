# src/esg/extractors/table_grid_extractor.py
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Mapping

import pdfplumber

logger = logging.getLogger(__name__)


# ============================================================
# Helpers
# ============================================================

def _norm_text(s: str) -> str:
    """
    Normalize a text fragment:
    - lowercase
    - strip accents
    - collapse non-alphanumeric to spaces
    - collapse repeated spaces
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.strip().lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_unit(u: str) -> str:
    """Normalize unit strings for comparison."""
    return u.lower().replace(" ", "").replace("³", "3")


# Minimal multilingual synonyms for the 3 supported KPIs
_HARDCODED = {
    "total_ghg_emissions": [
        "total ghg emissions", "ghg emissions total",
        "treibhausgasemissionen gesamt",
        "emissions totales de ges",
    ],
    "energy_consumption": [
        "total energy consumption", "energy consumption total",
        "gesamtenergieverbrauch",
        "consommation totale d energie",
    ],
    "water_withdrawal": [
        "total water withdrawal", "water withdrawal total",
        "gesamtwasserentnahme",
        "prelevement total d eau",
    ],
}


def _build_synonyms(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """
    Combine schema synonyms with minimal multilingual synonyms,
    returning normalized kpi → list[str].
    """
    out = {}
    for code, meta in kpi_schema.items():
        base = meta.get("synonyms") or [code.replace("_", " ")]
        combined = base + _HARDCODED.get(code, [])
        out[code] = [_norm_text(s) for s in combined if _norm_text(s)]
    return out


def _build_units(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Return {code: allowed_units} directly from the schema."""
    return {code: (meta.get("units") or []) for code, meta in kpi_schema.items()}


# ============================================================
# Header detection (minimal heuristic)
# ============================================================

def _detect_cols(header: List[str]) -> Dict[str, int]:
    """
    Determine column indices for KPI, unit, and value.
    Uses minimal multilingual cues.
    """
    norm = [_norm_text(h) for h in header]
    kpi = unit = value = None

    for i, h in enumerate(norm):
        if any(t in h for t in ["kpi", "metric", "kennzahl", "indicateur", "indicator"]):
            kpi = i
        if any(t in h for t in ["unit", "einheit", "unite"]):
            unit = i
        if any(t in h for t in ["wert", "valeur", "value"]):
            value = i
        if re.match(r"20\d{2}$", h) and value is None:  # e.g., "2022"
            value = i

    n = len(header)

    return {
        "kpi": kpi or 0,
        "unit": unit if unit is not None else (1 if n > 1 else 0),
        "value": value if value is not None else (2 if n > 2 else n - 1),
    }


# ============================================================
# Extract from a single table_grid
# ============================================================

def _extract_table_grid(
    rows: List[List[str]],
    syns: Mapping[str, List[str]],
    units: Mapping[str, List[str]],
) -> Dict[str, Dict[str, Any]]:

    if not rows or len(rows) < 2:
        return {}

    header = rows[0]
    col = _detect_cols(header)
    results = {}

    for row in rows[1:]:
        if not row:
            continue

        # Ensure column indexes exist
        if max(col["kpi"], col["unit"], col["value"]) >= len(row):
            continue

        kpi_raw = (row[col["kpi"]] or "").strip()
        unit_raw = (row[col["unit"]] or "").strip()
        value_raw = (row[col["value"]] or "").strip()

        if not kpi_raw or not value_raw:
            continue

        kpi_norm = _norm_text(kpi_raw)

        # Match KPI using normalized synonyms
        matched = None
        for code, sylist in syns.items():
            if any(s in kpi_norm for s in sylist):
                matched = code
                break
        if not matched:
            continue

        allowed_units = units.get(matched, [])
        raw_unit = unit_raw or None

        # Ignore cases where "unit" column accidentally contains digits
        if raw_unit and re.search(r"\d", raw_unit):
            raw_unit = None

        # Unit inside parentheses in KPI name overrides column unit
        if raw_unit is None:
            m = re.search(r"\(([^)]+)\)", kpi_raw)
            if m:
                raw_unit = m.group(1).strip()

        # Resolve to schema unit
        final_unit = None
        if raw_unit:
            norm_ru = _norm_unit(raw_unit)
            for u in allowed_units:
                if norm_ru == _norm_unit(u):
                    final_unit = u
                    break

        # Single-unit KPIs default when unit missing
        if final_unit is None and len(allowed_units) == 1:
            final_unit = allowed_units[0]
            raw_unit = allowed_units[0]

        results[matched] = {
            "raw_value": value_raw,
            "raw_unit": raw_unit,
            "value": value_raw,   # normalizer will parse
            "unit": final_unit,   # normalizer will finalize
            "confidence": 0.9,
        }

    return results


# ============================================================
# Public API
# ============================================================

def extract_kpis_tables_grid(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:

    logger.info("table_grid: extracting from %s", pdf_path)

    syns = _build_synonyms(kpi_schema)
    units = _build_units(kpi_schema)
    aggregated: Dict[str, Dict[str, Any]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables_grid = page.extract_tables() or []
                for table_grid in tables_grid:
                    if not table_grid:
                        continue

                    hits = _extract_table_grid(table_grid, syns, units)

                    # First-hit rule: keep only the first occurrence
                    for code, entry in hits.items():
                        if code not in aggregated:
                            aggregated[code] = entry

    except Exception as exc:
        logger.warning("table_grid: pdfplumber failed for %s: %s", pdf_path, exc)
        return {}

    return aggregated

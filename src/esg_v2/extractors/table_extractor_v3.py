# src/esg_v2/extractors/table_extractor_v3.py
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
    """Lowercase + remove accents + collapse punctuation."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.strip().lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_unit(u: str) -> str:
    """Normalize unit for comparison."""
    return u.lower().replace(" ", "").replace("³", "3")


# Minimal multilingual synonyms for your 3 KPIs
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
    """Schema synonyms + multilingual synonyms."""
    out = {}
    for code, meta in kpi_schema.items():
        syns = list(meta.get("synonyms") or [code.replace("_", " ")])
        syns += _HARDCODED.get(code, [])
        out[code] = [_norm_text(s) for s in syns if _norm_text(s)]
    return out


def _build_units(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    return {code: (meta.get("units") or []) for code, meta in kpi_schema.items()}


# ============================================================
# Header detection (minimal)
# ============================================================

def _detect_cols(header: List[str]) -> Dict[str, int]:
    """Return {kpi, unit, value} column indexes using simple heuristics."""
    norm = [_norm_text(h) for h in header]
    kpi = unit = value = None

    for i, h in enumerate(norm):
        if any(t in h for t in ["kpi", "metric", "kennzahl", "indicateur", "indicator"]):
            kpi = i
        if any(t in h for t in ["unit", "einheit", "unite"]):
            unit = i
        if any(t in h for t in ["wert", "valeur", "value"]):
            value = i
        if re.match(r"20\d{2}$", h) and value is None:
            value = i

    n = len(header)
    return {
        "kpi": kpi or 0,
        "unit": unit if unit is not None else (1 if n > 1 else 0),
        "value": value if value is not None else (2 if n > 2 else n - 1),
    }


# ============================================================
# Extract from a single table
# ============================================================

def _extract_from_table(
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

        # bounds check
        if max(col["kpi"], col["unit"], col["value"]) >= len(row):
            continue

        kpi_raw = (row[col["kpi"]] or "").strip()
        unit_raw = (row[col["unit"]] or "").strip()
        value_raw = (row[col["value"]] or "").strip()

        if not kpi_raw or not value_raw:
            continue

        kpi_norm = _norm_text(kpi_raw)

        # match KPI
        matched = None
        for code, sylist in syns.items():
            if any(s in kpi_norm for s in sylist):
                matched = code
                break
        if not matched:
            continue

        allowed = units.get(matched, [])

        # unit resolution
        if unit_raw and re.search(r"\d", unit_raw):
            unit_raw = ""

        raw_unit = unit_raw or None

        # KPI column parentheses override
        if raw_unit is None:
            m = re.search(r"\(([^)]+)\)", kpi_raw)
            if m:
                raw_unit = m.group(1).strip()

        final_unit = None
        if raw_unit:
            ru = _norm_unit(raw_unit)
            for u in allowed:
                if ru == _norm_unit(u):
                    final_unit = u
                    break

        if final_unit is None and len(allowed) == 1:
            final_unit = allowed[0]
            raw_unit = allowed[0]

        results[matched] = {
            "raw_value": value_raw,
            "raw_unit": raw_unit,
            "value": value_raw,      # ✓ v3 normalizer will parse this
            "unit": final_unit,      # ✓ v3 normalizer will finalize this
            "confidence": 0.9,
        }

    return results


# ============================================================
# Public API
# ============================================================

def extract_kpis_from_tables_v3(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:

    logger.info("table_v3: extracting from %s", pdf_path)

    syns = _build_synonyms(kpi_schema)
    units = _build_units(kpi_schema)
    aggregated: Dict[str, Dict[str, Any]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table:
                        continue

                    hits = _extract_from_table(table, syns, units)

                    # first-hit rule
                    for code, entry in hits.items():
                        if code not in aggregated:
                            aggregated[code] = entry

    except Exception as exc:
        logger.warning("table_v3: pdfplumber failed for %s: %s", pdf_path, exc)
        return {}

    return aggregated

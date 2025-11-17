# src/esg_v2/extractors/table_extractor_v3.py
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Mapping, Optional

import pdfplumber

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_text(s: str) -> str:
    """
    Lowercase, remove accents, strip punctuation to make matching robust
    across EN / DE / FR KPI labels.
    Example:
        "Émissions totales de GES" -> "emissions totales de ges"
        "Prélèvement total d’eau"  -> "prelevement total d eau"
    """
    if not s:
        return ""
    s = s.strip().lower()

    # Normalize accents
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

    # Replace non-alphanumeric with spaces
    s = re.sub(r"[^a-z0-9]+", " ", s)

    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


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


def _parse_number_locale_aware(num: Optional[str]) -> Optional[float]:
    """
    Parse numbers like:
        '123,400'      -> 123400.0
        '123.400'      -> 123400.0  (DE thousands)
        '123 400'      -> 123400.0  (FR thousands)
        '1,200,000'    -> 1200000.0
        '1.200.000'    -> 1200000.0
        '1 200 000'    -> 1200000.0
        '123.45'       -> 123.45
        '123,45'       -> 123.45
    """
    if not num:
        return None

    s = num.strip().replace("\u00A0", " ")  # non-breaking space -> normal
    if not s:
        return None

    # Remove spaces for easier regexes
    s_no_space = s.replace(" ", "")

    # Pattern A: pure thousands grouping with comma/dot, e.g. 1,200,000 or 1.200.000
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        digits = re.sub(r"[.,]", "", s_no_space)
        try:
            return float(digits)
        except Exception:
            return None

    # Pattern B: thousands with spaces: 1 200 000
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        digits = s.replace(" ", "")
        try:
            return float(digits)
        except Exception:
            return None

    # Pattern C: simple integer
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # Pattern D: decimal with one separator: 123.45 or 123,45
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # Fallback: remove obvious thousand-like separators and try
    digits = re.sub(r"[ ,.]", "", s)
    try:
        return float(digits)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# KPI metadata helpers
# ---------------------------------------------------------------------------

# Hard-coded multi-lingual synonyms to sit on top of whatever the schema has.
# We keep this small and focused on your three test KPIs.
_HARDCODED_SYNONYMS: Dict[str, List[str]] = {
    "total_ghg_emissions": [
        # English
        "total ghg emissions",
        "ghg emissions total",
        # German
        "treibhausgasemissionen gesamt",
        # French
        "emissions totales de ges",
    ],
    "energy_consumption": [
        # English
        "total energy consumption",
        "energy consumption total",
        # German
        "gesamtenergieverbrauch",
        # French
        "consommation totale d energie",
        "consommation totale d energie",
    ],
    "water_withdrawal": [
        # English
        "total water withdrawal",
        "water withdrawal total",
        # German
        "gesamtwasserentnahme",
        # French
        "prelevement total d eau",
    ],
}


def _build_kpi_synonyms_v3(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """
    Build normalized synonym lists per KPI for v3, combining:
    - schema-provided synonyms
    - a small set of multi-lingual hard-coded synonyms (EN/DE/FR)
    All synonyms are normalized with _normalize_text for robust matching.
    """
    kpi_syns: Dict[str, List[str]] = {}

    for code, meta in kpi_schema.items():
        syns = meta.get("synonyms") or []
        # Fallback: use code name as a loose synonym
        if not syns:
            syns = [code.replace("_", " ")]

        # Add hard-coded multi-lingual syns if present
        extra = _HARDCODED_SYNONYMS.get(code, [])
        syns = list(syns) + list(extra)

        # Normalize all
        normalized_syns = []
        for s in syns:
            ns = _normalize_text(s)
            if ns:
                normalized_syns.append(ns)

        kpi_syns[code] = list(dict.fromkeys(normalized_syns))  # deduplicate, keep order

    return kpi_syns


def _build_kpi_units(kpi_schema: Mapping[str, Any]) -> Dict[str, List[str]]:
    """
    Build normalized unit lists per KPI from the schema (keep original tokens).
    """
    kpi_units: Dict[str, List[str]] = {}
    for code, meta in kpi_schema.items():
        raw_units = meta.get("units") or []
        kpi_units[code] = list(raw_units)
    return kpi_units


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

def _detect_column_roles(header: List[str]) -> Dict[str, int]:
    """
    Detect which column is KPI label, which is unit, which is value, based on
    simple heuristics on header text. Works for EN / DE / FR examples:
        EN: ["KPI", "Unit", "2024"]
        DE: ["Kennzahl", "Einheit", "Wert"]
        FR: ["Indicateur", "Unité", "Valeur"]
    Returns a dict like {"kpi": 0, "unit": 1, "value": 2}
    """
    header_norm = [_normalize_text(h) for h in header]

    kpi_idx: Optional[int] = None
    unit_idx: Optional[int] = None
    value_idx: Optional[int] = None

    for i, h in enumerate(header_norm):
        if any(tok in h for tok in ["kpi", "metric", "kennzahl", "indicateur", "indicator"]):
            kpi_idx = i
        if any(tok in h for tok in ["unit", "einheit", "unite"]):  # "unite" is normalized "Unité"
            unit_idx = i
        if any(tok in h for tok in ["wert", "valeur", "value"]):
            value_idx = i
        # Year-like headers: 2024, 2023 etc.
        if re.match(r"20\d{2}$", h):
            # treat as value column if not already set
            if value_idx is None:
                value_idx = i

    # Fallbacks if not detected
    n_cols = len(header)
    if kpi_idx is None:
        kpi_idx = 0
    if unit_idx is None and n_cols >= 2:
        unit_idx = 1
    if value_idx is None and n_cols >= 3:
        value_idx = 2

    return {
        "kpi": kpi_idx,
        "unit": unit_idx if unit_idx is not None else 1,
        "value": value_idx if value_idx is not None else (n_cols - 1),
    }


# ---------------------------------------------------------------------------
# Core extraction logic
# ---------------------------------------------------------------------------

def _extract_from_table(
    rows: List[List[str]],
    kpi_syns: Mapping[str, List[str]],
    kpi_units: Mapping[str, List[str]],
) -> Dict[str, Dict[str, Any]]:
    """
    Given a single pdfplumber table (list of rows), try to extract KPI rows.
    Returns a sparse dict: only KPIs with hits are included.
    """
    if not rows or len(rows) < 2:
        return {}

    header = rows[0]
    col_roles = _detect_column_roles(header)
    kpi_col = col_roles["kpi"]
    unit_col = col_roles["unit"]
    value_col = col_roles["value"]

    results: Dict[str, Dict[str, Any]] = {}

    for row in rows[1:]:
        if not row:
            continue

        # Make sure row has enough columns
        if max(kpi_col, unit_col, value_col) >= len(row):
            continue

        kpi_label_raw = (row[kpi_col] or "").strip()
        unit_raw = (row[unit_col] or "").strip()
        value_raw = (row[value_col] or "").strip()

        if not kpi_label_raw or not value_raw:
            continue

        kpi_label_norm = _normalize_text(kpi_label_raw)

        # Try to identify which KPI this row refers to
        matched_code: Optional[str] = None
        for code, syns in kpi_syns.items():
            for syn in syns:
                if syn and syn in kpi_label_norm:
                    matched_code = code
                    break
            if matched_code:
                break

        if not matched_code:
            continue

        # Resolve unit against schema units
        canonical_units = kpi_units.get(matched_code, [])
        raw_unit = unit_raw or None
        unit: Optional[str] = None

        if raw_unit and canonical_units:
            ru_norm = _normalize_unit_token(raw_unit)
            for cu in canonical_units:
                cu_norm = _normalize_unit_token(cu)
                if cu_norm == ru_norm:
                    unit = cu
                    break

        # Parse value
        value = _parse_number_locale_aware(value_raw)

        logger.info(
            "table_v3 (grid) hit for %s: raw_value='%s', raw_unit='%s', kpi_label='%s'",
            matched_code,
            value_raw,
            raw_unit,
            kpi_label_raw,
        )

        # Only keep first hit per KPI for now
        if matched_code not in results:
            results[matched_code] = {
                "raw_value": value_raw,
                "raw_unit": raw_unit,
                "value": value,
                "unit": unit,
                "confidence": 0.9,  # grid-based, so slightly higher than v2 text heuristic
            }

    return results


def extract_kpis_from_tables_v3(
    pdf_path: str,
    kpi_schema: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    v3 'table' extractor (grid-mode with pdfplumber).

    - Uses pdfplumber's table extraction (lattice/stream combined via `extract_tables`).
    - Interprets header rows to detect KPI / unit / value columns.
    - Matches KPI labels using multi-lingual (EN/DE/FR) synonyms.
    - Parses numeric values with locale-aware thousands / decimal handling.
    - Resolves units to canonical KPI units when possible.

    Returns a sparse dict: only KPIs with hits are present.
    The returned entries are already normalized, of the form:

        {
            "total_ghg_emissions": {
                "raw_value": "123,400",
                "raw_unit": "tCO2e",
                "value": 123400.0,
                "unit": "tCO2e",
                "confidence": 0.9,
            },
            ...
        }
    """
    logger.info("table_v3 (grid): extracting tables from %s", pdf_path)

    kpi_syns = _build_kpi_synonyms_v3(kpi_schema)
    kpi_units = _build_kpi_units(kpi_schema)

    aggregated: Dict[str, Dict[str, Any]] = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_tables = page.extract_tables() or []

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("table_v3 DEBUG: page %d, %d tables", page_idx + 1, len(page_tables))

                for t_idx, table in enumerate(page_tables):
                    # table is List[List[str]]
                    if not table:
                        continue

                    # Optional debug: show raw tables at DEBUG level
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("--- table_v3 DEBUG: page %d, table %d ---", page_idx + 1, t_idx)
                        for r in table:
                            logger.debug("    %s", r)

                    table_hits = _extract_from_table(table, kpi_syns, kpi_units)

                    # Merge hits, keeping the first occurrence per KPI
                    for code, entry in table_hits.items():
                        if code not in aggregated:
                            aggregated[code] = entry

    except Exception as exc:
        logger.warning(
            "table_v3 (grid): failed to read '%s' via pdfplumber: %s", pdf_path, exc
        )
        return {}

    if not aggregated:
        logger.info("table_v3 (grid): no KPI hits found in %s", pdf_path)

    return aggregated

"""
PyMuPDF Table Extractor (layout-based)
--------------------------------------

Stable + robust version:
- Works for: SIEMENS, UNILEVER, test_table_esg
- Conservative (minimal false positives)
- Synonym-expanding keyword search
- Fuzzy-matching for CO₂ vs CO2, plural forms, spacing
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, cast

import fitz  # type: ignore[import]

from esg_system.config import load_config
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)


# ============================================================
# Normalization helpers
# ============================================================

def _normalize_text(t: str) -> str:
    """
    Make text uniform:
    - lowercase
    - remove hyphens/dashes
    - CO₂ → CO2
    - remove trailing 's'
    """
    t = t.lower()
    t = t.replace("co₂", "co2").replace("co\u2082", "co2")
    t = t.replace("-", " ").replace("–", " ")
    t = re.sub(r"\s+", " ", t).strip()

    return t


def _expand_synonyms(words: List[str]) -> List[str]:
    """
    Expand synonyms by:
    - pluralizing / singularizing
    - removing hyphens
    - CO₂/CO2 variations
    """
    expanded = set()

    for s in words:
        s_norm = _normalize_text(s)
        expanded.add(s_norm)
        expanded.add(s_norm.rstrip("s"))
        expanded.add(s_norm.replace(" co2e", " co2e"))
        expanded.add(s_norm.replace(" co2", " co2"))

        # remove hyphens entirely
        expanded.add(s_norm.replace(" ", ""))

    return list(expanded)


def _normalize_unit(u: str) -> str:
    """Normalize CO₂/e units."""
    u = u.lower().strip()
    u = u.replace("co₂", "co2").replace("co\u2082", "co2")
    u = u.replace(" ", "")
    return u


def _normalize_number(raw: str) -> Optional[float]:
    cleaned = raw.replace(" ", "").replace(",", "")
    try:
        return float(cleaned)
    except Exception:
        return None


# ============================================================
# Ranges
# ============================================================

def _value_in_reasonable_range(kpi: str, value: float) -> bool:
    ranges = {
        "total_ghg_emissions": (10.0, 1_000_000_000.0),
        "energy_consumption": (10.0, 1_000_000_000.0),
        "water_withdrawal": (10.0, 1_000_000_000.0),
    }
    lo, hi = ranges.get(kpi, (0, 10**12))
    return lo <= value <= hi


# ============================================================
# Text extraction
# ============================================================

def _extract_page_words(page) -> List[Dict[str, Any]]:
    wlist = page.get_text("words")
    return [
        {"x0": w[0], "y0": w[1], "x1": w[2], "y1": w[3], "text": w[4]}
        for w in wlist
    ]


def _group_words_into_rows(words: List[Dict[str, Any]], threshold: float = 5.0) -> List[List[Dict[str, Any]]]:
    if not words:
        return []

    words_sorted = sorted(words, key=lambda w: (w["y0"], w["x0"]))
    rows: List[List[Dict[str, Any]]] = []

    for w in words_sorted:
        placed = False
        for row in rows:
            if abs(row[0]["y0"] - w["y0"]) < threshold:
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])

    for row in rows:
        row.sort(key=lambda w: w["x0"])

    return rows


def _rows_to_text(rows: List[List[Dict]]) -> List[str]:
    return [" ".join(word["text"] for word in row) for row in rows]


# ============================================================
# KPI Detection
# ============================================================

def _row_matches_synonyms(text_block: str, syns: List[str]) -> bool:
    text_norm = _normalize_text(text_block)
    return any(s in text_norm for s in syns)


def _search_inline_units(row_text: str, units: List[str]) -> List[Tuple[float, str]]:
    matches = []
    text = row_text

    for u in units:
        u_norm = _normalize_unit(u)
        pattern = rf"(-?\d[\d,\.]*)\s*{re.escape(u_norm)}"
        for raw in re.findall(pattern, text.lower().replace(" ", ""), flags=re.IGNORECASE):
            num = _normalize_number(raw)
            if num is not None:
                matches.append((num, u))
    return matches


def _search_numeric_only(row_text: str, units_block: str) -> List[Tuple[float, str]]:
    matches = []
    nums = re.findall(r"(-?\d[\d,\.]*)", row_text)
    for raw in nums:
        num = _normalize_number(raw)
        if num is None:
            continue
        matches.append((num, None))
    return matches


def _search_row_for_kpi(
    row_text: str,
    prev_text: str,
    next_text: str,
    kpi_code: str,
    synonyms: List[str],
    units: List[str],
) -> List[Tuple[float, str]]:
    block = " ".join([prev_text, row_text, next_text])

    # 1. fuzzy synonyms
    if not _row_matches_synonyms(block, synonyms):
        return []

    # 2. inline unit patterns
    inline = _search_inline_units(row_text, units)
    if inline:
        return inline

    # 3. numeric-only if unit is elsewhere
    nums = _search_numeric_only(row_text, block)
    if nums:
        # assign nearest unit if available
        for i, (val, _) in enumerate(nums):
            for u in units:
                if _normalize_unit(u) in block.replace(" ", ""):
                    nums[i] = (val, u)
                    break
        return nums

    return []


# ============================================================
# MAIN EXTRACTOR
# ============================================================

def extract_kpis_from_fitz(pdf_path: str) -> Dict[str, ExtractorResult]:
    logger.info("Running PyMuPDF table extractor (layout-based)…")

    cfg = load_config()
    kpi_rules = cfg.mapping_rules["universal_kpis"]

    results: Dict[str, Dict[str, Any]] = {
        code: {"value": None, "unit": None, "confidence": 0.0}
        for code in kpi_rules.keys()
    }

    # Pre-expand synonyms
    expanded_rules = {}
    for code, meta in kpi_rules.items():
        syns = meta.get("synonyms", [])
        expanded_rules[code] = {
            "synonyms": _expand_synonyms(syns),
            "units": [_normalize_unit(u) for u in meta.get("units", [])],
        }

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.warning(f"PyMuPDF failed to open '{pdf_path}': {e}")
        return cast(Dict[str, ExtractorResult], results)

    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            words = _extract_page_words(page)
            if not words:
                continue

            rows = _group_words_into_rows(words)
            row_texts = _rows_to_text(rows)

            for kpi_code, meta in expanded_rules.items():
                if results[kpi_code]["value"] is not None:
                    continue

                synonyms = meta["synonyms"]
                units = meta["units"]

                for i, row in enumerate(row_texts):
                    prev_text = row_texts[i - 1] if i > 0 else ""
                    next_text = row_texts[i + 1] if i < len(row_texts) - 1 else ""

                    matches = _search_row_for_kpi(
                        row_text=row,
                        prev_text=prev_text,
                        next_text=next_text,
                        kpi_code=kpi_code,
                        synonyms=synonyms,
                        units=units,
                    )

                    if not matches:
                        continue

                    # pick first stable match
                    value, unit_raw = matches[0]
                    if unit_raw is None:
                        continue

                    if not _value_in_reasonable_range(kpi_code, value):
                        continue

                    logger.info(
                        "PyMuPDF hit %s: value=%s, unit=%s, page=%d",
                        kpi_code, value, unit_raw, page_index + 1,
                    )

                    results[kpi_code] = {
                        "value": value,
                        "unit": unit_raw,
                        "confidence": 0.88,
                    }
                    break

    finally:
        doc.close()

    return cast(Dict[str, ExtractorResult], results)

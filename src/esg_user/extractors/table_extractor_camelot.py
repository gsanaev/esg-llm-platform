"""
Smart Table Filtering (STF) Camelot Extractor
---------------------------------------------

This module:
- Extracts tables using Camelot
- Filters irrelevant pages based on ESG-related text
- Scores tables using moderately strict rules
- Applies basic scaling based on header context (thousand / million)
- Returns highest-scoring values per KPI
- Optionally caches results per PDF for speed
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import camelot
import pdfplumber

from esg_system.config import load_config
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)

# Bump this if logic changes and you want to invalidate old cache
CACHE_VERSION = "camelot_stf_v1"


# -------------------------------------------------------------------
# 1. Basic helpers
# -------------------------------------------------------------------

def _normalize_number(raw: str) -> Optional[float]:
    """
    Normalize a numeric string into a float:
    - remove commas, spaces, parentheses
    - handle simple minus sign variants
    """
    if raw is None:
        return None

    cleaned = raw.replace(",", "").replace(" ", "")
    cleaned = cleaned.replace("(", "").replace(")", "")
    cleaned = cleaned.replace("−", "-")

    # strip trailing non-numeric junk (e.g. "123.4m3" -> "123.4")
    cleaned = re.sub(r"[^\d\.\-]", "", cleaned)

    try:
        return float(cleaned)
    except Exception:
        return None


def _contains_kpi_keywords(text: str, keywords: List[str]) -> bool:
    text_l = text.lower()
    return any(k.lower() in text_l for k in keywords)


def _contains_units(text: str, units: List[str]) -> bool:
    text_l = text.lower()
    return any(u.lower() in text_l for u in units)


def _value_in_reasonable_range(kpi_code: str, value: float) -> bool:
    """
    Moderately strict ranges to filter clearly wrong values.
    These are generic and not company-specific.
    """
    ranges = {
        "total_ghg_emissions": (100, 100_000_000),
        "energy_consumption": (100, 1_000_000_000),
        "water_withdrawal": (100, 1_000_000_000),
    }

    low, high = ranges.get(kpi_code, (0, 10**12))
    return low <= value <= high


def _scale_value(value: float, header_text: str) -> float:
    """
    Scale values when headers indicate thousand/million units.
    Very generic, applies across many ESG tables.
    """
    h = header_text.lower()

    # Rough but useful heuristics
    if "thousand" in h or "k " in h or "kwh" in h and "mwh" not in h:
        return value * 1_000
    if "million" in h or "m " in h or "mm3" in h or "million m3" in h:
        return value * 1_000_000

    return value


# -------------------------------------------------------------------
# 2. Page filtering
# -------------------------------------------------------------------

PAGE_KEYWORDS = [
    # Direct KPI indicators
    "ghg", "co2e", "co₂e", "tco2", "scope 1", "scope 2",
    "mwh", "kwh", "gwh", "energy consumption",
    "m3", "m³", "water withdrawal", "water use",

    # Table-specific words
    "table", "metric", "kpi", "indicator",
    "environmental data", "environmental performance",

    # Strong ESG signal
    "environmental data",
    "kpi table",
    "esg data",
]



def _is_page_relevant(text: str) -> bool:
    """
    Strict relevance:
    Page must contain BOTH:
       1) a KPI-related numeric unit (tCO2e, MWh, m3...)
       2) AND a table/indicator keyword
    """
    t = text.lower()

    unit_keywords = ["tco2", "co2e", "mwh", "kwh", "gwh", "m3", "m³"]
    strong_indicators = ["table", "environmental", "kpi", "indicator"]

    has_unit = any(u in t for u in unit_keywords)
    has_indicator = any(s in t for s in strong_indicators)

    return has_unit and has_indicator



def _find_relevant_pages(pdf_path: str, max_pages: int = 200) -> List[int]:
    """
    Use pdfplumber to scan pages and select those likely to contain ESG KPIs.
    Generic for all companies.
    """
    relevant: List[int] = []

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return relevant

    try:
        with pdfplumber.open(pdf_file) as pdf:
            num_pages = min(len(pdf.pages), max_pages)
            for idx in range(num_pages):
                page = pdf.pages[idx]
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                if _is_page_relevant(text):
                    relevant.append(idx + 1)  # 1-based for Camelot
    except Exception as e:
        logger.warning(f"Failed to scan pages for relevance: {e}")
        return []

    return relevant


# -------------------------------------------------------------------
# 3. Table scoring (your logic, slightly generalized)
# -------------------------------------------------------------------

def _score_table(
    table_text: str,
    kpi_code: str,
    synonyms: List[str],
    units: List[str],
) -> int:
    """
    Score table relevance for a KPI (moderately strict).
    Based on:
    - presence of KPI keywords
    - presence of candidate units
    - numeric density
    - penalizing too small numbers
    - penalizing very wide tables
    """
    score = 0
    text = table_text.lower()

    # 1. KPI keywords
    if _contains_kpi_keywords(text, synonyms):
        score += 5

    # 2. Units present
    if _contains_units(text, units):
        score += 5

    # 3. Header or first row mentions KPI
    first_lines = "\n".join(text.split("\n")[:3])
    if _contains_kpi_keywords(first_lines, synonyms):
        score += 3

    # 4. Many numeric cells
    nums = re.findall(r"\d[\d,\.]*", text)
    if len(nums) >= 3:
        score += 2

    # 5. Penalize too small numbers (often not real KPIs)
    small_values = []
    for n in nums:
        stripped = n.replace(",", "")
        if stripped.replace(".", "", 1).isdigit():
            try:
                v = float(stripped)
                if v < 50:
                    small_values.append(v)
            except Exception:
                pass
    if small_values:
        score -= 2

    # 6. Penalize very wide tables (many tab-like separators)
    if table_text.count("\t") > 8:
        score -= 2

    return score


# -------------------------------------------------------------------
# 4. Caching helpers (cache final KPI results per PDF)
# -------------------------------------------------------------------

def _get_cache_path(pdf_path: str) -> Path:
    """
    Compute a cache file path based on:
    - PDF absolute path
    - PDF mtime
    - internal version
    """
    pdf = Path(pdf_path).resolve()
    try:
        mtime = os.path.getmtime(pdf)
    except OSError:
        mtime = 0

    key_raw = f"{pdf}|{mtime}|{CACHE_VERSION}"
    cache_key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()

    cache_dir = pdf.parent / ".esg_table_cache"
    cache_dir.mkdir(exist_ok=True)

    return cache_dir / f"{cache_key}.json"


def _load_cache(pdf_path: str) -> Optional[Dict[str, ExtractorResult]]:
    cache_file = _get_cache_path(pdf_path)
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # basic sanity: must be dict[str, dict]
        if isinstance(data, dict):
            return data  # type: ignore[return-value]
    except Exception as e:
        logger.warning(f"Failed to load Camelot cache: {e}")

    return None


def _save_cache(pdf_path: str, data: Dict[str, ExtractorResult]) -> None:
    cache_file = _get_cache_path(pdf_path)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning(f"Failed to save Camelot cache: {e}")


# -------------------------------------------------------------------
# 5. Main extraction function
# -------------------------------------------------------------------

def extract_kpis_from_camelot_filtered(
    pdf_path: str,
    use_cache: bool = False,
    force_refresh: bool = False,
) -> Dict[str, ExtractorResult]:
    """
    Extract KPI values from tables using Camelot with Smart Table Filtering.

    - Filter pages by ESG-related keywords
    - Use Camelot (lattice) on those pages
    - Score tables per KPI
    - Extract numbers+units with range checks and simple scaling
    - Optionally cache per-PDF results
    """

    logger.info("Running Smart Table Filtering (Camelot)…")

    if use_cache and not force_refresh:
        cached = _load_cache(pdf_path)
        if cached is not None:
            logger.info("Returning Camelot results from cache.")
            return cached  # type: ignore[return-value]

    cfg = load_config()
    # use mapping_rules with synonyms/units
    rules: Dict[str, Dict[str, List[str]]] = cfg.mapping_rules["universal_kpis"]

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return {}

    # 1) Find relevant pages
    relevant_pages = _find_relevant_pages(pdf_path)
    if not relevant_pages:
        logger.warning("No relevant pages found for table extraction. Skipping Camelot.")
        results: Dict[str, ExtractorResult] = {
            k: {"value": None, "unit": None, "confidence": 0.0}
            for k in rules.keys()
        }
        if use_cache:
            _save_cache(pdf_path, results)
        return results

    pages_str = ",".join(str(p) for p in relevant_pages)
    logger.info(f"Relevant pages for tables: {pages_str}")

    # 2) Run Camelot on relevant pages only
    try:
        tables = camelot.read_pdf(pdf_path, pages=pages_str, flavor="lattice")
        logger.info(f"Extracted {tables.n} tables (raw).")
    except Exception as e:
        logger.warning(f"Camelot failed on {pdf_path}: {e}")
        results = {
            k: {"value": None, "unit": None, "confidence": 0.0}
            for k in rules.keys()
        }
        if use_cache:
            _save_cache(pdf_path, results)
        return results

    results: Dict[str, ExtractorResult] = {}

    # 3) Loop over KPIs
    for kpi_code, meta in rules.items():
        synonyms = meta.get("synonyms", [])
        units = meta.get("units", [])

        best_score = -999
        best_value: Optional[float] = None
        best_unit: Optional[str] = None

        # Loop over tables
        for idx, table in enumerate(tables):
            df = table.df

            # Build plain text representation of the table
            table_text = "\n".join(" ".join(row) for _, row in df.iterrows())

            score = _score_table(table_text, kpi_code, synonyms, units)
            if score < 5:
                # table deemed irrelevant for this KPI
                continue

            # Try to extract numbers+units
            # Pattern: number + optional spaces + unit
            for unit in units:
                unit_esc = re.escape(unit)
                pattern = rf"(-?\d[\d,\.\s]*)\s*{unit_esc}"

                for match in re.finditer(pattern, table_text, flags=re.IGNORECASE):
                    raw_num = match.group(1)
                    value = _normalize_number(raw_num)

                    if value is None:
                        continue

                    # optional header scaling based on first row
                    header_text = " ".join(df.iloc[0].astype(str).tolist())
                    value = _scale_value(value, header_text)

                    if not _value_in_reasonable_range(kpi_code, value):
                        continue

                    # Accept this candidate if table's score is better
                    if score > best_score:
                        best_score = score
                        best_value = value
                        best_unit = unit

                        logger.info(
                            "SmartTable hit %s: value=%s, unit=%s, "
                            "score=%s, table=%s",
                            kpi_code,
                            value,
                            unit,
                            score,
                            idx,
                        )

        # Finalize KPI
        if best_value is not None:
            results[kpi_code] = {
                "value": best_value,
                "unit": best_unit,
                "confidence": 0.9,
            }
        else:
            # No good table-based value found for this KPI
            results[kpi_code] = {
                "value": None,
                "unit": None,
                "confidence": 0.0,
            }

    if use_cache:
        _save_cache(pdf_path, results)

    return results

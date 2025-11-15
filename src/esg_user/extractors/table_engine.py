from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Tuple

from esg_user.types import ExtractorResult
from esg_user.extractors.table_extractor_camelot import (
    extract_kpis_from_camelot_filtered,
)
from esg_user.extractors.table_extractor_fitz import extract_kpis_from_fitz
from esg_user.extractors.table_extractor import (
    extract_kpis_from_tables as extract_kpis_from_pdfplumber,
)

logger = logging.getLogger(__name__)

RawResultDict = Mapping[str, Any]

SOURCE_PRIORITY: Dict[str, int] = {
    "camelot": 3,
    "fitz": 2,
    "plumber": 1,
}


def _safe_call_table_extractor(
    name: str, func, pdf_path: str
) -> Dict[str, Dict[str, Any]]:
    """
    Run a table extractor safely.
    Returns an empty dict if it fails or returns a non-dict.
    """
    try:
        logger.info("Table engine: running %s extractor…", name)
        res = func(pdf_path)
        if not isinstance(res, dict):
            logger.warning(
                "Table engine: extractor %s returned non-dict (%s)",
                name,
                type(res),
            )
            return {}
        return res
    except Exception as e:
        logger.error("Table engine: extractor %s failed: %s", name, e)
        return {}


def _coerce_extractor_result(raw: Mapping[str, Any]) -> ExtractorResult:
    """
    Convert arbitrary raw dict → ExtractorResult.
    Missing fields default safely.
    """
    return {
        "value": raw.get("value"),
        "unit": raw.get("unit"),
        "confidence": float(raw.get("confidence", 0.0)),
        "source": raw.get("source", []),
        "raw_value": raw.get("raw_value"),
        "raw_unit": raw.get("raw_unit"),
    }


def _pick_best_table_candidate(
    candidates: List[Tuple[str, ExtractorResult]]
) -> ExtractorResult:
    """
    Choose the best candidate from table sources using:
    - confidence
    - source priority
    """
    if not candidates:
        return {
            "value": None,
            "unit": None,
            "confidence": 0.0,
            "source": [],
            "raw_value": None,
            "raw_unit": None,
        }

    def score(item: Tuple[str, ExtractorResult]) -> Tuple[float, int]:
        src, res = item
        return (float(res.get("confidence", 0.0)), SOURCE_PRIORITY.get(src, 0))

    _, winner = max(candidates, key=score)
    return winner


def extract_kpis_from_tables_unified(
    pdf_path: str,
    kpi_codes: List[str],
) -> Dict[str, ExtractorResult]:
    """
    Unified Table Extraction Engine.
    """
    logger.info("Table engine: starting unified table extraction for %s", pdf_path)

    camelot_res = _safe_call_table_extractor(
        "camelot", extract_kpis_from_camelot_filtered, pdf_path
    )
    fitz_res = _safe_call_table_extractor(
        "fitz", extract_kpis_from_fitz, pdf_path
    )
    plumber_res = _safe_call_table_extractor(
        "plumber", extract_kpis_from_pdfplumber, pdf_path
    )

    final: Dict[str, ExtractorResult] = {}

    for code in kpi_codes:
        candidates: List[Tuple[str, ExtractorResult]] = []

        # Camelot
        camel_raw = camelot_res.get(code)
        if camel_raw and camel_raw.get("value") is not None:
            candidates.append(("camelot", _coerce_extractor_result(camel_raw)))

        # Fitz
        fitz_raw = fitz_res.get(code)
        if fitz_raw and fitz_raw.get("value") is not None:
            candidates.append(("fitz", _coerce_extractor_result(fitz_raw)))

        # Plumber
        plumber_raw = plumber_res.get(code)
        if plumber_raw and plumber_raw.get("value") is not None:
            candidates.append(("plumber", _coerce_extractor_result(plumber_raw)))

        final[code] = _pick_best_table_candidate(candidates)

    logger.info("Table engine: unified extraction complete.")
    logger.debug("Table engine final results: %s", final)

    return final

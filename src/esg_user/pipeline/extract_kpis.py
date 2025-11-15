from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Callable

from esg_system.config import load_config

from esg_user.extractors.regex_extractor import extract_kpis_regex
from esg_user.extractors.nlp_extractor import extract_kpis_nlp
from esg_user.extractors.llm_extractor import extract_kpis_llm
from esg_user.extractors.table_engine import extract_kpis_from_tables_unified

from esg_user.pipeline.fusion import fuse_all
from esg_user.pipeline.normalize_kpis import normalize_kpis

from esg_user.types import ExtractorResultDict

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Safe extractor wrapper
# -------------------------------------------------------------------

def _safe_run_extractor(
    name: str,
    func: Callable[..., Dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Run an extractor safely. If it fails or returns non-dict, return {}.
    """
    try:
        logger.debug("Running extractor: %s", name)
        result = func(*args, **kwargs)
        if not isinstance(result, dict):
            logger.warning(
                "Extractor %s returned non-dict result of type %s",
                name,
                type(result),
            )
            return {}
        return result
    except Exception as e:  # pragma: no cover
        logger.error("Extractor %s failed: %s", name, e)
        return {}


# -------------------------------------------------------------------
# Main orchestration
# -------------------------------------------------------------------

def extract_all_kpis(
    text: str,
    pdf_path: Optional[str] = None,
) -> Dict[str, ExtractorResultDict]:
    """
    Run all extractors (regex, NLP, table, LLM), normalize, and fuse.
    Returns Dict[str, ExtractorResultDict].
    """
    logger.info("Starting combined KPI extraction…")
    cfg = load_config()

    kpi_schema = cfg.universal_kpis
    kpi_codes: list[str] = list(kpi_schema.keys())

    # ---------------------------------------------------------
    # Text-based extractors
    # ---------------------------------------------------------

    raw_regex: Dict[str, Any] = _safe_run_extractor("regex", extract_kpis_regex, text)
    raw_nlp: Dict[str, Any] = _safe_run_extractor("nlp", extract_kpis_nlp, text)

    # Normalize into ExtractorResultDict (with units/value normalization)
    regex_res: Dict[str, ExtractorResultDict] = normalize_kpis(raw_regex)
    nlp_res: Dict[str, ExtractorResultDict] = normalize_kpis(raw_nlp)

    # ---------------------------------------------------------
    # Table engine
    # ---------------------------------------------------------

    if pdf_path:
        logger.info("Running unified table extraction engine…")
        raw_table: Dict[str, Any] = extract_kpis_from_tables_unified(pdf_path, kpi_codes)
    else:
        raw_table = {
            code: {
                "value": None,
                "unit": None,
                "confidence": 0.0,
                "source": [],
                "raw_value": None,
                "raw_unit": None,
            }
            for code in kpi_codes
        }

    table_res: Dict[str, ExtractorResultDict] = normalize_kpis(raw_table)

    # ---------------------------------------------------------
    # LLM extractor
    # ---------------------------------------------------------

    raw_llm: Dict[str, Any] = _safe_run_extractor("llm", extract_kpis_llm, text)
    llm_res: Dict[str, ExtractorResultDict] = normalize_kpis(raw_llm)

    # ---------------------------------------------------------
    # Fusion
    # ---------------------------------------------------------

    logger.info("Fusing extractor outputs…")

    final = fuse_all(
        regex_res=regex_res,
        nlp_res=nlp_res,
        table_res=table_res,
        llm_res=llm_res,
        kpi_codes=kpi_codes,
    )

    logger.info("Fusion complete.")
    logger.debug("Final extracted KPIs: %s", final)

    return final

from typing import Dict, Any, Optional
from esg_system.config import load_config
from esg_user.extractors.regex_extractor import extract_kpis_regex
from esg_user.extractors.nlp_extractor import extract_kpis_nlp
from esg_user.extractors.table_extractor import extract_kpis_from_tables
from esg_user.extractors.llm_extractor import extract_kpis_llm


def merge_kpi_sources(
    base: Dict[str, Dict[str, Any]],
    new: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Merge results by filling missing values in base with values from new.
    If base[kpi]['value'] is None and new[kpi]['value'] is not None -> take new.
    Units follow same rule.
    """
    result = base.copy()

    for kpi_code, item in new.items():
        if kpi_code not in result:
            result[kpi_code] = item
            continue

        if result[kpi_code].get("value") is None and item.get("value") is not None:
            result[kpi_code] = item

    return result


def extract_all_kpis(text: str, pdf_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Unified orchestrator for KPI extraction.
    Order of priority:
    1. Regex extractor
    2. NLP extractor
    3. Table extractor (if PDF provided)
    4. LLM extractor (fallback)
    """

    cfg = load_config()
    kpi_codes = list(cfg.universal_kpis.keys())

    # Initialize result with empty structure
    results = {
        kpi: {"value": None, "unit": None}
        for kpi in kpi_codes
    }

    # 1 Regex extraction
    regex_results = extract_kpis_regex(text)
    results = merge_kpi_sources(results, regex_results)

    # 2 NLP extraction
    nlp_results = extract_kpis_nlp(text)
    results = merge_kpi_sources(results, nlp_results)

    # 3 Table extraction (only if PDF available)
    if pdf_path is not None:
        table_results = extract_kpis_from_tables(pdf_path)
        results = merge_kpi_sources(results, table_results)

    # 4 LLM extraction (fallback)
    llm_results = extract_kpis_llm(text)
    results = merge_kpi_sources(results, llm_results)

    return results

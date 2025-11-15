import re
from typing import Dict, List, Optional
import pdfplumber
from esg_system.config import load_config
from esg_user.types import ExtractorResult

import logging
logger = logging.getLogger(__name__)


def _clean(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.split()).strip().lower()


def _extract_number_from_cell(cell: str) -> Optional[float]:
    """Extract the first numeric value from a table cell."""
    if not cell:
        return None

    match = re.search(r"([0-9][0-9,\.]*)", cell)
    if not match:
        return None

    raw = match.group(1).replace(",", "")

    try:
        return float(raw)
    except ValueError:
        return None


def _find_unit_in_row(row_text: str, allowed_units: List[str]) -> Optional[str]:
    """Find unit by scanning entire row text."""
    for unit in allowed_units:
        if re.search(rf"\b{re.escape(unit)}\b", row_text, re.IGNORECASE):
            return unit
    return None


def extract_kpis_from_tables(pdf_path: str) -> Dict[str, ExtractorResult]:
    """
    Extract KPIs from tables inside a PDF.
    """

    logger.debug(f"Running table extractor on PDF: {pdf_path}")

    cfg = load_config()
    rules = cfg.mapping_rules.get("universal_kpis", {})
    results: Dict[str, ExtractorResult] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            logger.debug(f"Page {page_num}: found {len(tables)} tables")

            for table in tables:
                for row in table:
                    if not row:
                        logger.warning(f"Skipping empty row in table on page {page_num}")
                        continue

                    cleaned = [_clean(c) for c in row if c is not None]
                    row_text = " ".join(cleaned)

                    # Check each KPI
                    for kpi_code, kpi_info in rules.items():
                        synonyms = [s.lower() for s in kpi_info.get("synonyms", [])]
                        units = kpi_info.get("units", [])

                        # If no synonym found in row → skip
                        if not any(s in row_text for s in synonyms):
                            continue

                        # Extract numbers from the row (columns 2...n)
                        numeric_values = [
                            _extract_number_from_cell(c)
                            for c in cleaned[1:]
                        ]
                        numeric_values = [n for n in numeric_values if n is not None]

                        if not numeric_values:
                            logger.debug(
                                f"Table match for {kpi_code} on page {page_num}, "
                                f"but no numeric value found."
                            )
                            continue

                        value = numeric_values[0]
                        unit = _find_unit_in_row(row_text, units)

                        logger.info(
                            f"Table extractor hit {kpi_code}: "
                            f"value={value}, unit={unit}, page={page_num}"
                        )

                        results[kpi_code] = {
                            "value": value,
                            "unit": unit,
                            "confidence": 0.9
                        }

    return results

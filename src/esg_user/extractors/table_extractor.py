import re
from typing import Dict, Any, List, Optional
import pdfplumber
from esg_system.config import load_config


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


def extract_kpis_from_tables(pdf_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract KPIs from tables inside a PDF.
    Returns a dict like:
       { "total_ghg_emissions": {"value": 123400, "unit": "tCO2e"}, ... }
    """

    cfg = load_config()
    rules = cfg.mapping_rules.get("universal_kpis", {})
    results = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    if not row:
                        continue

                    # Clean cells
                    cleaned = [_clean(c) for c in row if c is not None]
                    row_text = " ".join(cleaned)

                    # Check each KPI
                    for kpi_code, kpi_info in rules.items():
                        synonyms = [s.lower() for s in kpi_info.get("synonyms", [])]
                        units = kpi_info.get("units", [])

                        # Check if row contains a synonym
                        if not any(s in row_text for s in synonyms):
                            continue

                        # Extract numeric value from any cell after the label
                        numeric_values = [
                            _extract_number_from_cell(c)
                            for c in cleaned[1:]  # skip first cell (label cell)
                        ]
                        numeric_values = [n for n in numeric_values if n is not None]

                        if not numeric_values:
                            continue

                        # Take the first numeric cell
                        value = numeric_values[0]

                        # Detect unit in the entire row
                        unit = _find_unit_in_row(row_text, units)

                        results[kpi_code] = {"value": value, "unit": unit}

    return results

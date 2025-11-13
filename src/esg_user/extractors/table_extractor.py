import re
from typing import Dict, Any, List, Optional
from esg_system.config import load_config
from esg_system.core.table_reader import extract_tables


# ---------------------------------------
# Helper functions
# ---------------------------------------

def normalize_number(s: str) -> Optional[float]:
    """Convert extracted numeric string into a float."""
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def find_numbers_in_row(row: List[str]) -> List[re.Match]:
    """Find all numeric regex matches in a row of cells."""
    pattern = re.compile(r"\b[0-9][0-9,\.]*\b")
    matches = []
    for cell in row:
        if not isinstance(cell, str):
            continue
        matches.extend(pattern.finditer(cell))
    return matches


def find_unit_in_cell(cell: str, allowed_units: List[str]) -> Optional[str]:
    """Check if a cell contains one of the allowed KPI units."""
    if not isinstance(cell, str):
        return None

    for unit in allowed_units:
        pattern = re.compile(rf"\b{re.escape(unit)}\b", re.IGNORECASE)
        if pattern.search(cell):
            return unit
    return None


# ---------------------------------------
# Main Extraction Function
# ---------------------------------------

def extract_kpis_from_tables(pdf_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract KPI values from tables found in the PDF.
    - Look for KPI synonyms in table cells.
    - If found in a row, extract numeric values in that row.
    - Extract unit if possible.
    """

    cfg = load_config()
    results = {}

    universal_rules = cfg.mapping_rules.get("universal_kpis", {})
    tables = extract_tables(pdf_path)

    for kpi_code, kpi_info in universal_rules.items():
        synonyms = kpi_info.get("synonyms", [])
        allowed_units = kpi_info.get("units", [])

        for table in tables:
            for row in table:

                # Convert None values to empty strings
                cleaned_row = [c if isinstance(c, str) else "" for c in row]

                # Check if any cell contains a synonym
                row_contains_kpi = False
                for synonym in synonyms:
                    syn_pattern = re.compile(rf"\b{re.escape(synonym)}\b", re.IGNORECASE)
                    if any(syn_pattern.search(cell) for cell in cleaned_row):
                        row_contains_kpi = True
                        break

                if not row_contains_kpi:
                    continue

                # Extract numbers from the row
                numbers = find_numbers_in_row(cleaned_row)
                if not numbers:
                    continue

                # Take the first numeric value (minimal version)
                number_match = numbers[0]
                value_raw = number_match.group()
                value = normalize_number(value_raw)

                # Try to detect units from any cell in the row
                unit = None
                for cell in cleaned_row:
                    unit = find_unit_in_cell(cell, allowed_units)
                    if unit:
                        break

                # Save and stop searching for this KPI
                if value is not None:
                    results[kpi_code] = {
                        "value": value,
                        "unit": unit
                    }
                    break  # Stop scanning rows for this KPI

            if kpi_code in results:
                break  # Stop scanning tables for this KPI

    return results

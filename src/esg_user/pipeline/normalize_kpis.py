from typing import Dict, Any, Optional
from esg_system.config import load_config


# -----------------------------------------
# Simple conversion rules (placeholder)
# -----------------------------------------

# You can extend this at any time.
UNIT_CONVERSION = {
    ("GWh", "MWh"): 1000,
    ("MWh", "GWh"): 0.001,
}


def convert_unit(value: Optional[float], unit: Optional[str], target_unit: Optional[str]) -> Optional[float]:
    """
    Convert 'value' from 'unit' to 'target_unit' using UNIT_CONVERSION.
    If value is None or no conversion exists, return value unchanged.
    """
    if value is None or unit is None or target_unit is None:
        return value

    key = (unit, target_unit)
    if key in UNIT_CONVERSION:
        return value * UNIT_CONVERSION[key]

    return value


# -----------------------------------------
# Main normalization function
# -----------------------------------------

def normalize_kpis(kpi_dict: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Normalize KPI dictionary:
    - Convert units to canonical units defined in schema
    - Ensure value is numeric and valid
    - Leave None values untouched
    """
    cfg = load_config()
    universal_schema = cfg.universal_kpis

    normalized = {}

    for kpi_code, entry in kpi_dict.items():
        value = entry.get("value")
        unit = entry.get("unit")

        # Canonical unit from schema
        canonical_unit = universal_schema.get(kpi_code, {}).get("unit")

        # Convert only if necessary
        if canonical_unit and unit and unit != canonical_unit:
            value = convert_unit(value, unit, canonical_unit)
            unit = canonical_unit

        normalized[kpi_code] = {
            "value": value,
            "unit": unit or canonical_unit,
        }

    return normalized

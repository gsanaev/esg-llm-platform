# src/esg_v2/tests/test_tables_v2.py

import json
from pathlib import Path

from esg_v2.extractors.table_extractor_v2 import extract_kpis_from_tables_v2
from esg_v2.normalization.table_normalizer_v2 import normalize_table_result_v2


SCHEMA_PATH = Path("src/esg_system/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/test_table_esg.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_v2_text_tables():
    kpi_schema = load_kpis()

    # Extract directly from PDF path
    raw = extract_kpis_from_tables_v2(str(PDF_PATH), kpi_schema)

    # Normalize
    normalized = normalize_table_result_v2(raw, kpi_schema)

    # Basic structure
    assert isinstance(normalized, dict)
    assert "total_ghg_emissions" in normalized

    # Validate the example table entry
    ghg = normalized["total_ghg_emissions"]

    assert ghg["value"] == 123400.0
    assert ghg["unit"] == "tCO2e"
    assert ghg["confidence"] == 0.85

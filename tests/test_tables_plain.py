# src/esg/tests/test_tables.py

import json
from pathlib import Path

from esg.extractors.table_plain_extractor import extract_kpis_tables_plain
from esg.normalization.table_plain_normalizer import normalize_table_plain_result


SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/test_table_esg.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_text_tables():
    kpi_schema = load_kpis()

    # Extract directly from PDF path
    raw = extract_kpis_tables_plain(str(PDF_PATH), kpi_schema)

    # Normalize
    normalized = normalize_table_plain_result(raw, kpi_schema)

    # Basic structure
    assert isinstance(normalized, dict)
    assert "total_ghg_emissions" in normalized

    # Validate the example table entry
    ghg = normalized["total_ghg_emissions"]

    assert ghg["value"] == 123400.0
    assert ghg["unit"] == "tCO2e"
    assert ghg["confidence"] == 0.85

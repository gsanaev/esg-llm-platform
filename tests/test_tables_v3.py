# tests/test_tables_v3.py
import json
from pathlib import Path

from esg_v2.extractors.table_extractor_v3 import extract_kpis_from_tables_v3
from esg_v2.normalization.table_normalizer_v3 import normalize_table_result_v3

SCHEMA_PATH = Path("src/esg_system/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/test_table_esg_grid_v3.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_v3_grid_tables():
    kpis = load_kpis()

    raw = extract_kpis_from_tables_v3(str(PDF_PATH), kpis)
    normalized = normalize_table_result_v3(raw, kpis)

    assert "total_ghg_emissions" in normalized
    assert normalized["total_ghg_emissions"]["value"] in (123400.0, 123400)

    assert "energy_consumption" in normalized
    assert normalized["energy_consumption"]["value"] == 500000.0

    assert "water_withdrawal" in normalized
    assert normalized["water_withdrawal"]["value"] == 1200000.0


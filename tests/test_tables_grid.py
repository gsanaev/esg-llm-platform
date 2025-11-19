# tests/test_tables_v3.py
import json
from pathlib import Path

from esg.extractors.table_grid_extractor import extract_kpis_tables_grid
from esg.normalization.table_grid_normalizer import normalize_table_grid_result

SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/test_table_esg_grid_v3.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_v3_grid_tables():
    kpis = load_kpis()

    raw = extract_kpis_tables_grid(str(PDF_PATH), kpis)
    normalized = normalize_table_grid_result(raw, kpis)

    assert "total_ghg_emissions" in normalized
    assert normalized["total_ghg_emissions"]["value"] in (123400.0, 123400)

    assert "energy_consumption" in normalized
    assert normalized["energy_consumption"]["value"] == 500000.0

    assert "water_withdrawal" in normalized
    assert normalized["water_withdrawal"]["value"] == 1200000.0


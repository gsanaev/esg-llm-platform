# tests/test_tables_plain.py
import json
from pathlib import Path

from esg.extractors.table_plain_extractor import (
    extract_kpi_candidates_tables_plain,
    extract_kpis_tables_plain,
)
from esg.normalization.table_plain_normalizer import normalize_table_plain_result

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/samples/esg_simple_mixed.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_text_tables():
    kpi_schema = load_kpis()
    raw = extract_kpis_tables_plain(str(PDF_PATH), kpi_schema)
    ghg_raw = raw["total_ghg_emissions"]

    assert ghg_raw["page"] == 1
    assert ghg_raw["source_context"]
    assert "123" in ghg_raw["source_context"]

    normalized = normalize_table_plain_result(raw, kpi_schema)

    assert isinstance(normalized, dict)
    assert "total_ghg_emissions" in normalized

    ghg = normalized["total_ghg_emissions"]
    assert ghg["value"] == 123400.0
    assert ghg["unit"] == "tCO2e"
    assert ghg["confidence"] == 0.85


def test_table_plain_preserves_multiple_candidates(tmp_path):
    pdf_path = tmp_path / "repeated_water_withdrawal_plain.pdf"

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    pdf.drawString(
        72,
        760,
        "Total water withdrawal | m3 | 1,200,000",
    )
    pdf.drawString(
        72,
        740,
        "Total water withdrawal | m3 | 1,250,000",
    )
    pdf.save()

    kpi_schema = load_kpis()

    candidates = extract_kpi_candidates_tables_plain(
        str(pdf_path),
        kpi_schema,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 2
    assert [entry["raw_value"] for entry in water] == [
        "1,200,000",
        "1,250,000",
    ]
    assert all(entry["page"] == 1 for entry in water)
    assert all(entry["source_context"] for entry in water)

    single_result = extract_kpis_tables_plain(
        str(pdf_path),
        kpi_schema,
    )

    assert single_result["water_withdrawal"]["raw_value"] == "1,200,000"

# tests/test_tables_grid.py
import json
from pathlib import Path

from esg.extractors.table_grid_extractor import (
    extract_kpi_candidates_tables_grid,
    extract_kpis_tables_grid,
)
from esg.normalization.table_grid_normalizer import normalize_table_grid_result

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/samples/esg_simple_table.pdf")   # updated


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_table_v3_grid_tables():
    kpis = load_kpis()

    raw = extract_kpis_tables_grid(str(PDF_PATH), kpis)
    ghg_raw = raw["total_ghg_emissions"]
    normalized = normalize_table_grid_result(raw, kpis)

    assert ghg_raw["page"] == 1
    assert ghg_raw["source_context"]
    assert "123" in ghg_raw["source_context"]
    assert "total_ghg_emissions" in normalized
    assert normalized["total_ghg_emissions"]["value"] in (123400.0, 123400)
    assert "energy_consumption" in normalized
    assert normalized["energy_consumption"]["value"] == 500000.0
    assert "water_withdrawal" in normalized
    assert normalized["water_withdrawal"]["value"] == 1200000.0


def test_table_grid_preserves_multiple_candidates(tmp_path):
    pdf_path = tmp_path / "repeated_water_withdrawal.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total water withdrawal", "m3", "1,200,000"],
        ["Total water withdrawal", "m3", "1,250,000"],
    ]

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )

    doc.build([table])

    candidates = extract_kpi_candidates_tables_grid(
        str(pdf_path),
        load_kpis(),
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 2
    assert [entry["raw_value"] for entry in water] == [
        "1,200,000",
        "1,250,000",
    ]
    assert all(entry["page"] == 1 for entry in water)
    assert all(entry["source_context"] for entry in water)

    legacy = extract_kpis_tables_grid(
        str(pdf_path),
        load_kpis(),
    )

    assert legacy["water_withdrawal"]["raw_value"] == "1,250,000"


def test_table_grid_preserves_location_context(tmp_path):
    pdf_path = tmp_path / "facility_water_withdrawal.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["Location", "KPI", "Unit", "2024"],
        [
            "Frankfurt facility",
            "Total water withdrawal",
            "m3",
            "350,000",
        ],
        [
            "Berlin facility",
            "Total water withdrawal",
            "m3",
            "280,000",
        ],
    ]

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )

    doc.build([table])

    candidates = extract_kpi_candidates_tables_grid(
        str(pdf_path),
        load_kpis(),
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 2
    assert [entry["raw_value"] for entry in water] == [
        "350,000",
        "280,000",
    ]
    assert [entry["location"] for entry in water] == [
        "Frankfurt facility",
        "Berlin facility",
    ]

    legacy = extract_kpis_tables_grid(
        str(pdf_path),
        load_kpis(),
    )

    assert legacy["water_withdrawal"]["location"] == "Berlin facility"


def test_table_grid_normalizes_qualitative_water_dependency(tmp_path):
    pdf_path = tmp_path / "water_dependency.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["KPI", "Unit", "2024"],
        ["Water dependency", "", "High dependency"],
    ]

    table = Table(data)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )

    doc.build([table])

    kpis = load_kpis()

    raw = extract_kpis_tables_grid(
        str(pdf_path),
        kpis,
    )

    assert raw["water_dependency"]["raw_value"] == "High dependency"
    assert raw["water_dependency"]["raw_unit"] is None

    normalized = normalize_table_grid_result(
        raw,
        kpis,
    )

    dependency = normalized["water_dependency"]

    assert dependency["value"] == "high dependency"
    assert dependency["unit"] is None

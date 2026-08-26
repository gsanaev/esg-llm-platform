# tests/test_pipeline.py
from pathlib import Path
import pytest
from esg.pipeline.pipeline import ESGPipelineV2, run_pipeline
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

PDF_TABLE = Path("data/samples/esg_simple_table.pdf")   # updated
PDF_NLP_ONLY = Path("data/samples/esg_simple_text.pdf") # updated

@pytest.fixture(autouse=True)
def disable_llm_api(monkeypatch):
    """
    Keep pipeline tests deterministic and independent of external API access.
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_pipeline_end_to_end():
    results = run_pipeline(str(PDF_TABLE))

    assert isinstance(results, list)
    assert results, "Pipeline returned an empty result list"

    by_code = {r.code: r for r in results}
    assert "total_ghg_emissions" in by_code

    ghg = by_code["total_ghg_emissions"]
    assert ghg.value == 123400.0
    assert ghg.unit.lower() in ("tco2e",)


def test_pipeline_with_nlp_fallback():
    results = run_pipeline(str(PDF_NLP_ONLY))

    by_code = {r.code: r for r in results}
    assert "total_ghg_emissions" in by_code

    ghg = by_code["total_ghg_emissions"]

    assert ghg.value == 123400.0
    assert ghg.unit.lower() in ("tco2e", "tco2e")
    assert ghg.source in (["regex"], ["nlp"], ["table"], ["table_v3"])

def test_pipeline_preserves_evidence_before_fusion():
    pipeline = ESGPipelineV2()

    results, evidence = pipeline.run_on_pdf_with_evidence(str(PDF_TABLE))

    assert results
    assert evidence

    methods = {candidate.extraction_method for candidate in evidence}

    assert methods
    assert methods.issubset({
        "table_grid",
        "table_plain",
        "regex",
        "nlp",
        "llm",
    })

    assert all(
        candidate.source_document == str(PDF_TABLE)
        for candidate in evidence
    )

    assert any(
        candidate.metric == "total_ghg_emissions"
        for candidate in evidence
    )


def test_pipeline_preserves_multiple_same_method_evidence(tmp_path):
    pdf_path = tmp_path / "repeated_water_pipeline.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions", "tCO2e", "123,400"],
        ["Total energy consumption", "MWh", "500,000"],
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

    pipeline = ESGPipelineV2()
    results, evidence = pipeline.run_on_pdf_with_evidence(
        str(pdf_path)
    )

    water_grid_evidence = [
        candidate
        for candidate in evidence
        if (
            candidate.metric == "water_withdrawal"
            and candidate.extraction_method == "table_grid"
        )
    ]

    assert len(water_grid_evidence) == 2

    assert [
        candidate.value_normalized
        for candidate in water_grid_evidence
    ] == [
        1_200_000.0,
        1_250_000.0,
    ]

    assert all(
        candidate.page == 1
        for candidate in water_grid_evidence
    )

    by_code = {
        result.code: result
        for result in results
    }

    assert by_code["water_withdrawal"].value == 1_250_000.0
    assert by_code["water_withdrawal"].source == ["table_grid"]

    reconciled = pipeline.run_on_pdf_reconciled(
        str(pdf_path)
    )

    by_metric = {
        result.metric: result
        for result in reconciled
    }

    water = by_metric["water_withdrawal"]

    assert water.status == "review_required"
    assert water.value is None
    assert water.conflict_flag is True
    assert water.review_required is True
    assert len(water.supporting_evidence) >= 2


def test_pipeline_produces_reconciled_results():
    pipeline = ESGPipelineV2()

    results = pipeline.run_on_pdf_reconciled(
        str(PDF_TABLE)
    )

    assert results

    by_metric = {
        result.metric: result
        for result in results
    }

    ghg = by_metric["total_ghg_emissions"]

    assert ghg.value == 123_400.0
    assert ghg.unit == "tCO2e"
    assert ghg.status == "accepted"
    assert ghg.conflict_flag is False
    assert ghg.review_required is False
    assert ghg.supporting_evidence


def test_pipeline_distinguishes_water_withdrawal_and_consumption(tmp_path):
    pdf_path = tmp_path / "water_metrics_pipeline.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions", "tCO2e", "123,400"],
        ["Total energy consumption", "MWh", "500,000"],
        ["Total water withdrawal", "m3", "1,200,000"],
        ["Total water consumption", "m3", "800,000"],
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

    pipeline = ESGPipelineV2()

    results, evidence = pipeline.run_on_pdf_with_evidence(
        str(pdf_path)
    )

    by_code = {
        result.code: result
        for result in results
    }

    assert by_code["water_withdrawal"].value == 1_200_000.0
    assert by_code["water_consumption"].value == 800_000.0

    withdrawal_values = {
        candidate.value_normalized
        for candidate in evidence
        if candidate.metric == "water_withdrawal"
        and candidate.value_normalized is not None
    }

    consumption_values = {
        candidate.value_normalized
        for candidate in evidence
        if candidate.metric == "water_consumption"
        and candidate.value_normalized is not None
    }

    assert 1_200_000.0 in withdrawal_values
    assert 800_000.0 not in withdrawal_values

    assert 800_000.0 in consumption_values
    assert 1_200_000.0 not in consumption_values

    reconciled = pipeline.run_on_pdf_reconciled(
        str(pdf_path)
    )

    by_metric = {
        result.metric: result
        for result in reconciled
    }

    withdrawal = by_metric["water_withdrawal"]
    consumption = by_metric["water_consumption"]

    assert withdrawal.value == 1_200_000.0
    assert withdrawal.unit == "m3"
    assert withdrawal.status == "accepted"
    assert withdrawal.conflict_flag is False
    assert withdrawal.review_required is False

    assert consumption.value == 800_000.0
    assert consumption.unit == "m3"
    assert consumption.status == "accepted"
    assert consumption.conflict_flag is False
    assert consumption.review_required is False


def test_pipeline_normalizes_water_stress_share(tmp_path):
    pdf_path = tmp_path / "water_stress_pipeline.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions", "tCO2e", "123,400"],
        ["Total energy consumption", "MWh", "500,000"],
        ["Total water withdrawal", "m3", "1,200,000"],
        ["Total water consumption", "m3", "800,000"],
        ["Water stress share", "%", "38"],
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

    pipeline = ESGPipelineV2()

    results, evidence = pipeline.run_on_pdf_with_evidence(
        str(pdf_path)
    )

    by_code = {
        result.code: result
        for result in results
    }

    stress = by_code["water_stress_share"]

    assert stress.value == 0.38
    assert stress.unit == "fraction"

    stress_evidence = [
        candidate
        for candidate in evidence
        if candidate.metric == "water_stress_share"
    ]

    assert stress_evidence
    assert all(
        candidate.value_normalized == 0.38
        for candidate in stress_evidence
    )
    assert all(
        candidate.unit_normalized == "fraction"
        for candidate in stress_evidence
    )

    reconciled = pipeline.run_on_pdf_reconciled(
        str(pdf_path)
    )

    by_metric = {
        result.metric: result
        for result in reconciled
    }

    stress = by_metric["water_stress_share"]

    assert stress.value == 0.38
    assert stress.unit == "fraction"
    assert stress.status == "accepted"
    assert stress.conflict_flag is False
    assert stress.review_required is False
    assert stress.supporting_evidence


def test_pipeline_preserves_facility_location_context(tmp_path):
    pdf_path = tmp_path / "facility_location_pipeline.pdf"

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

    pipeline = ESGPipelineV2()

    _, evidence = pipeline.run_on_pdf_with_evidence(
        str(pdf_path)
    )

    water_grid = [
        candidate
        for candidate in evidence
        if (
            candidate.metric == "water_withdrawal"
            and candidate.extraction_method == "table_grid"
        )
    ]

    assert len(water_grid) == 2

    assert [
        candidate.value_normalized
        for candidate in water_grid
    ] == [
        350_000.0,
        280_000.0,
    ]

    assert [
        candidate.location
        for candidate in water_grid
    ] == [
        "Frankfurt facility",
        "Berlin facility",
    ]

    reconciled = pipeline.run_on_pdf_reconciled(
        str(pdf_path)
    )

    by_metric = {
        result.metric: result
        for result in reconciled
    }

    water = by_metric["water_withdrawal"]

    assert water.status == "review_required"
    assert water.value is None
    assert water.location is None
    assert water.conflict_flag is False
    assert water.review_required is True

    known_locations = {
        candidate.location
        for candidate in water.supporting_evidence
        if candidate.location is not None
    }

    assert known_locations == {
        "Frankfurt facility",
        "Berlin facility",
    }


def test_pipeline_preserves_qualitative_water_dependency(tmp_path):
    pdf_path = tmp_path / "water_dependency_pipeline.pdf"

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

    pipeline = ESGPipelineV2()

    results, evidence = pipeline.run_on_pdf_with_evidence(
        str(pdf_path)
    )

    dependency_evidence = [
        candidate
        for candidate in evidence
        if (
            candidate.metric == "water_dependency"
            and candidate.extraction_method == "table_grid"
        )
    ]

    assert len(dependency_evidence) == 1

    candidate = dependency_evidence[0]

    assert candidate.value_raw == "High dependency"
    assert candidate.value_normalized == "high dependency"
    assert candidate.unit_raw is None
    assert candidate.unit_normalized is None

    by_code = {
        result.code: result
        for result in results
    }

    dependency_result = by_code["water_dependency"]

    assert dependency_result.value == "high dependency"
    assert dependency_result.unit is None
    assert dependency_result.source == ["table_grid"]

    reconciled = pipeline.run_on_pdf_reconciled(
        str(pdf_path)
    )

    by_metric = {
        result.metric: result
        for result in reconciled
    }

    dependency = by_metric["water_dependency"]

    assert dependency.value == "high dependency"
    assert dependency.unit is None
    assert dependency.status == "accepted"
    assert dependency.conflict_flag is False
    assert dependency.review_required is False
    assert dependency.supporting_evidence

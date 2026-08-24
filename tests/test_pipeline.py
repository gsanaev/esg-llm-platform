# tests/test_pipeline.py
from pathlib import Path
from esg.pipeline.pipeline import ESGPipelineV2, run_pipeline
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

PDF_TABLE = Path("data/samples/esg_simple_table.pdf")   # updated
PDF_NLP_ONLY = Path("data/samples/esg_simple_text.pdf") # updated


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

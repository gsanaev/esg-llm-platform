# tests/test_pipeline.py
from pathlib import Path
from esg.pipeline.pipeline import ESGPipelineV2, run_pipeline

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

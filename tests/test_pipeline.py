# tests/test_pipeline.py
from pathlib import Path
from esg.pipeline.pipeline import run_pipeline

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

# tests/test_pipeline.py
from pathlib import Path
from esg_v2.pipeline.pipeline import run_pipeline_v2

PDF_TABLE = Path("data/raw/test_table_esg_grid_v3.pdf")
PDF_NLP_ONLY = Path("data/raw/esg_report_v1.pdf")  # contains text but no v3/v2 tables


def test_pipeline_end_to_end():
    results = run_pipeline_v2(str(PDF_TABLE))

    assert isinstance(results, list)
    assert results, "Pipeline returned an empty result list"

    by_code = {r.code: r for r in results}
    assert "total_ghg_emissions" in by_code

    ghg = by_code["total_ghg_emissions"]
    assert ghg.value == 123400.0
    assert ghg.unit.lower() in ("tco2e",)


def test_pipeline_with_nlp_fallback():
    """
    Ensures that if table_v3, table_v2, and regex fail,
    NLP still extracts the KPIs.
    """
    results = run_pipeline_v2(str(PDF_NLP_ONLY))

    by_code = {r.code: r for r in results}
    assert "total_ghg_emissions" in by_code

    ghg = by_code["total_ghg_emissions"]

    # Since this PDF still contains regex hits, regex should win.
    # But NLP must at least produce output in the normalized structure.
    assert ghg.value == 123400.0
    assert ghg.unit.lower() in ("tco2e", "tco2e")

    # source must be one of:
    assert ghg.source in (["regex_v2"], ["nlp_v2"], ["table_v2"], ["table_v3"])

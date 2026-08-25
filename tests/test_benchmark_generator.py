from pathlib import Path

import pdfplumber

from esg.benchmark.generator import generate_benchmark_pdfs


TRUTH_PATH = Path("data/benchmark/truth/benchmark_truth.yaml")
CASES_PATH = Path("data/benchmark/cases/benchmark_cases.yaml")


def _extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_generate_benchmark_pdfs(tmp_path):
    paths = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    assert [path.name for path in paths] == [
        "alpha_structured_table.pdf",
        "alpha_clean_narrative.pdf",
        "beta_locale_table.pdf",
        "beta_mixed_units.pdf",
    ]
    assert all(path.is_file() for path in paths)

    texts = {
        path.name: _extract_pdf_text(path)
        for path in paths
    }

    table_text = texts["alpha_structured_table.pdf"]
    assert "synthetic_alpha" in table_text
    assert "123,400" in table_text
    assert "500,000" in table_text
    assert "1,200,000" in table_text
    assert "Total water consumption" in table_text
    assert "800,000" in table_text
    assert "Water stress share" in table_text
    assert "Water dependency" in table_text
    assert "high dependency" in table_text
    assert "%" in table_text
    assert "38" in table_text

    narrative_text = texts["alpha_clean_narrative.pdf"]
    assert "synthetic_alpha" in narrative_text
    assert "123,400" in narrative_text
    assert "500,000" in narrative_text
    assert "1,200,000" in narrative_text
    assert "800,000" in narrative_text
    assert "water-stressed areas" in narrative_text
    assert "high dependency" in narrative_text
    assert "%" in narrative_text
    assert "38" in narrative_text

    locale_text = texts["beta_locale_table.pdf"]
    assert "synthetic_beta" in locale_text
    assert "87.250" in locale_text
    assert "318.000" in locale_text
    assert "740.000" in locale_text
    assert "510.000" in locale_text
    assert "Water stress share" in locale_text
    assert "Water dependency" in locale_text
    assert "moderate dependency" in locale_text
    assert "%" in locale_text
    assert "62" in locale_text

    mixed_text = texts["beta_mixed_units.pdf"]
    assert "synthetic_beta" in mixed_text
    assert "GWh" in mixed_text
    assert "318" in mixed_text
    assert "318,000" not in mixed_text
    assert "740,000" in mixed_text
    assert "510,000" in mixed_text
    assert "Water stress share" in mixed_text
    assert "Water dependency" in mixed_text
    assert "moderate dependency" in mixed_text
    assert "%" in mixed_text
    assert "62" in mixed_text
    assert all(
        "None" not in text
        for text in texts.values()
    )

from pathlib import Path

import pdfplumber

from esg.benchmark.generator import generate_benchmark_pdfs


TRUTH_PATH = Path("data/benchmark/truth/benchmark_truth.yaml")


def _extract_pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_generate_benchmark_pdfs(tmp_path):
    paths = generate_benchmark_pdfs(TRUTH_PATH, tmp_path)

    assert [path.name for path in paths] == [
        "synthetic_alpha.pdf",
        "synthetic_beta.pdf",
    ]
    assert all(path.is_file() for path in paths)

    alpha_text = _extract_pdf_text(paths[0])
    beta_text = _extract_pdf_text(paths[1])

    assert "synthetic_alpha" in alpha_text
    assert "2024" in alpha_text
    assert "123,400" in alpha_text
    assert "500,000" in alpha_text
    assert "1,200,000" in alpha_text

    assert "synthetic_beta" in beta_text
    assert "87,250" in beta_text
    assert "318,000" in beta_text
    assert "740,000" in beta_text

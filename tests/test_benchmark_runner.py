from pathlib import Path

from esg.benchmark.generator import generate_benchmark_pdfs
from esg.benchmark.runner import run_benchmark_method
from esg.config import load_config

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import json
import os
from unittest.mock import patch

TRUTH_PATH = Path("data/benchmark/truth/benchmark_truth.yaml")
CASES_PATH = Path("data/benchmark/cases/benchmark_cases.yaml")


def test_run_benchmark_method_table_grid(tmp_path):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    alpha_table = next(
        path
        for path in generated
        if path.name == "alpha_structured_table.pdf"
    )

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(alpha_table),
        method="table_grid",
        kpi_schema=schema,
    )

    assert predictions["total_ghg_emissions"]["value"] == 123_400.0
    assert predictions["total_ghg_emissions"]["unit"] == "tCO2e"

    assert predictions["energy_consumption"]["value"] == 500_000.0
    assert predictions["energy_consumption"]["unit"] == "MWh"

    assert predictions["water_withdrawal"]["value"] == 1_200_000.0
    assert predictions["water_withdrawal"]["unit"] == "m3"

    assert predictions["water_consumption"]["value"] == 800_000.0
    assert predictions["water_consumption"]["unit"] == "m3"

    assert predictions["water_stress_share"]["value"] == 0.38
    assert predictions["water_stress_share"]["unit"] == "fraction"

    assert predictions["water_dependency"]["value"] == "high dependency"
    assert predictions["water_dependency"]["unit"] is None


def test_run_benchmark_method_table_plain_has_no_structured_table_hits(
    tmp_path,
):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    alpha_table = next(
        path
        for path in generated
        if path.name == "alpha_structured_table.pdf"
    )

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(alpha_table),
        method="table_plain",
        kpi_schema=schema,
    )

    assert predictions == {}


def test_run_benchmark_method_table_plain_pipe_row(tmp_path):
    pdf_path = tmp_path / "plain_table.pdf"

    pdf = canvas.Canvas(
        str(pdf_path),
        pagesize=A4,
    )
    pdf.drawString(
        72,
        760,
        "Total water withdrawal | m3 | 1,200,000",
    )
    pdf.save()

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(pdf_path),
        method="table_plain",
        kpi_schema=schema,
    )

    water = predictions["water_withdrawal"]

    assert water["value"] == 1_200_000.0
    assert water["unit"] == "m3"


def test_run_benchmark_method_regex_on_clean_narrative(tmp_path):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    alpha_narrative = next(
        path
        for path in generated
        if path.name == "alpha_clean_narrative.pdf"
    )

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(alpha_narrative),
        method="regex",
        kpi_schema=schema,
    )

    assert predictions["total_ghg_emissions"]["value"] == 123_400.0
    assert predictions["total_ghg_emissions"]["unit"] == "tCO2e"

    assert predictions["energy_consumption"]["value"] == 500_000.0
    assert predictions["energy_consumption"]["unit"] == "MWh"

    assert predictions["water_withdrawal"]["value"] == 1_200_000.0
    assert predictions["water_withdrawal"]["unit"] == "m3"

    assert predictions["water_consumption"]["value"] == 800_000.0
    assert predictions["water_consumption"]["unit"] == "m3"

    assert predictions["water_stress_share"]["value"] == 0.38
    assert predictions["water_stress_share"]["unit"] == "fraction"

    assert "water_dependency" not in predictions


def test_run_benchmark_method_nlp_on_clean_narrative(tmp_path):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    alpha_narrative = next(
        path
        for path in generated
        if path.name == "alpha_clean_narrative.pdf"
    )

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(alpha_narrative),
        method="nlp",
        kpi_schema=schema,
    )

    assert predictions["total_ghg_emissions"]["value"] == 123_400.0
    assert predictions["total_ghg_emissions"]["unit"] == "tCO2e"

    assert predictions["energy_consumption"]["value"] == 500_000.0
    assert predictions["energy_consumption"]["unit"] == "MWh"

    assert predictions["water_withdrawal"]["value"] == 1_200_000.0
    assert predictions["water_withdrawal"]["unit"] == "m3"

    assert predictions["water_consumption"]["value"] == 800_000.0
    assert predictions["water_consumption"]["unit"] == "m3"

    assert predictions["water_stress_share"]["value"] == 0.38
    assert predictions["water_stress_share"]["unit"] == "fraction"

    assert "water_dependency" not in predictions


LLM_BENCHMARK_RESPONSE = {
    "total_ghg_emissions": {
        "raw_value": "123,400",
        "raw_unit": "tCO2e",
    },
    "energy_consumption": {
        "raw_value": "500,000",
        "raw_unit": "MWh",
    },
    "water_withdrawal": {
        "raw_value": "1,200,000",
        "raw_unit": "m3",
    },
    "water_consumption": {
        "raw_value": "800,000",
        "raw_unit": "m3",
    },
    "water_stress_share": {
        "raw_value": "38",
        "raw_unit": "%",
    },
    "water_dependency": {
        "raw_value": "High dependency",
        "raw_unit": None,
    },
}


class MockLLMChoice:
    def __init__(self):
        self.message = type(
            "m",
            (),
            {
                "content": json.dumps(
                    LLM_BENCHMARK_RESPONSE
                )
            },
        )


class MockLLMCompletion:
    choices = [MockLLMChoice()]


@patch.dict(
    os.environ,
    {"OPENAI_API_KEY": "dummy"},
)
@patch(
    "openai.resources.chat.completions.Completions.create"
)
def test_run_benchmark_method_llm_on_clean_narrative(
    mock_create,
    tmp_path,
):
    mock_create.return_value = MockLLMCompletion()

    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    alpha_narrative = next(
        path
        for path in generated
        if path.name == "alpha_clean_narrative.pdf"
    )

    schema = load_config().universal_kpis

    predictions = run_benchmark_method(
        str(alpha_narrative),
        method="llm",
        kpi_schema=schema,
    )

    assert predictions["total_ghg_emissions"]["value"] == 123_400.0
    assert predictions["total_ghg_emissions"]["unit"] == "tCO2e"

    assert predictions["energy_consumption"]["value"] == 500_000.0
    assert predictions["energy_consumption"]["unit"] == "MWh"

    assert predictions["water_withdrawal"]["value"] == 1_200_000.0
    assert predictions["water_withdrawal"]["unit"] == "m3"

    assert predictions["water_consumption"]["value"] == 800_000.0
    assert predictions["water_consumption"]["unit"] == "m3"

    assert predictions["water_stress_share"]["value"] == 0.38
    assert predictions["water_stress_share"]["unit"] == "fraction"

    assert predictions["water_dependency"]["value"] == "high dependency"
    assert predictions["water_dependency"]["unit"] is None

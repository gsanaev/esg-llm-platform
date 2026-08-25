from pathlib import Path

from esg.benchmark.generator import generate_benchmark_pdfs
from esg.benchmark.runner import run_benchmark_method
from esg.config import load_config


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

from pathlib import Path

from esg.benchmark.case_evaluation import evaluate_benchmark_case
from esg.benchmark.cases import load_benchmark_cases
from esg.benchmark.generator import generate_benchmark_pdfs
from esg.benchmark.truth import load_benchmark_truth
from esg.config import load_config


TRUTH_PATH = Path("data/benchmark/truth/benchmark_truth.yaml")
CASES_PATH = Path("data/benchmark/cases/benchmark_cases.yaml")


def test_evaluate_benchmark_case_regex_against_hidden_truth(tmp_path):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    pdf_path = next(
        path
        for path in generated
        if path.name == "alpha_clean_narrative.pdf"
    )

    truth = load_benchmark_truth(TRUTH_PATH)
    cases = load_benchmark_cases(CASES_PATH)

    case = next(
        item
        for item in cases
        if item["case_id"] == "alpha_clean_narrative"
    )

    schema = load_config().universal_kpis

    result = evaluate_benchmark_case(
        str(pdf_path),
        case=case,
        truth=truth,
        method="regex",
        kpi_schema=schema,
    )

    assert result["case_id"] == "alpha_clean_narrative"
    assert result["company_id"] == "synthetic_alpha"
    assert result["method"] == "regex"

    predictions = result["predictions"]

    assert predictions["total_ghg_emissions"]["value"] == 123_400.0
    assert predictions["water_stress_share"]["value"] == 0.38
    assert "water_dependency" not in predictions

    summary = result["evaluation"]["summary"]

    assert summary["detection_precision"] == 1.0
    assert summary["detection_recall"] == 5 / 6
    assert summary["numeric_value_accuracy"] == 1.0
    assert summary["unit_accuracy"] == 1.0
    assert summary["extraction_coverage"] == 5 / 6

    dependency = result["evaluation"]["metrics"]["water_dependency"]

    assert dependency["expected_present"] is True
    assert dependency["predicted_present"] is False
    assert dependency["value_correct"] is False
    assert summary["location_accuracy"] == 0.0

    withdrawal = result["evaluation"]["metrics"]["water_withdrawal"]

    assert withdrawal["location_correct"] is False
    assert summary["reporting_year_accuracy"] == 0.0

    withdrawal = result["evaluation"]["metrics"]["water_withdrawal"]

    assert withdrawal["year_correct"] is False



def test_evaluate_benchmark_case_table_grid_location_against_hidden_truth(
    tmp_path,
):
    generated = generate_benchmark_pdfs(
        TRUTH_PATH,
        CASES_PATH,
        tmp_path,
    )

    pdf_path = next(
        path
        for path in generated
        if path.name == "alpha_structured_table.pdf"
    )

    truth = load_benchmark_truth(TRUTH_PATH)
    cases = load_benchmark_cases(CASES_PATH)

    case = next(
        item
        for item in cases
        if item["case_id"] == "alpha_structured_table"
    )

    schema = load_config().universal_kpis

    result = evaluate_benchmark_case(
        str(pdf_path),
        case=case,
        truth=truth,
        method="table_grid",
        kpi_schema=schema,
    )

    summary = result["evaluation"]["summary"]

    assert summary["location_accuracy"] == 1.0

    for metric in result["evaluation"]["metrics"].values():
        assert metric["location_correct"] is True

    assert summary["reporting_year_accuracy"] == 1.0

    for metric in result["evaluation"]["metrics"].values():
        assert metric["year_correct"] is True

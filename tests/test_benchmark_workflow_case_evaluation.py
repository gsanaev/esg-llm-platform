from pathlib import Path

from esg.benchmark.cases import load_benchmark_cases
from esg.benchmark.generator import generate_benchmark_pdfs
from esg.benchmark.workflow_case_evaluation import (
    evaluate_benchmark_workflow_case,
)
from unittest.mock import patch

TRUTH_PATH = Path(
    "data/benchmark/truth/benchmark_truth.yaml"
)
CASES_PATH = Path(
    "data/benchmark/cases/benchmark_cases.yaml"
)


@patch(
    "esg.pipeline.pipeline.extract_kpis_llm",
    return_value={},
)
def test_evaluate_benchmark_workflow_conflict_case(
    _mock_llm,
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
        if path.name
        == "alpha_conflicting_water_withdrawal.pdf"
    )

    cases = load_benchmark_cases(CASES_PATH)

    case = next(
        item
        for item in cases
        if item["case_id"]
        == "alpha_conflicting_water_withdrawal"
    )

    result = evaluate_benchmark_workflow_case(
        str(pdf_path),
        case=case,
    )

    assert result["case_id"] == (
        "alpha_conflicting_water_withdrawal"
    )

    summary = result["evaluation"]["summary"]

    assert summary["conflict_detection_accuracy"] == 1.0
    assert summary["review_flag_accuracy"] == 1.0

    water = result["evaluation"]["metrics"][
        "water_withdrawal"
    ]

    assert water["actual_conflict_flag"] is True
    assert water["conflict_correct"] is True
    assert water["actual_review_required"] is True
    assert water["review_correct"] is True


@patch(
    "esg.pipeline.pipeline.extract_kpis_llm",
    return_value={},
)
def test_evaluate_benchmark_workflow_missing_case(
    _mock_llm,
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
        if path.name
        == "alpha_missing_water_consumption.pdf"
    )

    cases = load_benchmark_cases(CASES_PATH)

    case = next(
        item
        for item in cases
        if item["case_id"]
        == "alpha_missing_water_consumption"
    )

    result = evaluate_benchmark_workflow_case(
        str(pdf_path),
        case=case,
    )

    summary = result["evaluation"]["summary"]

    assert summary["conflict_detection_accuracy"] == 1.0
    assert summary["review_flag_accuracy"] == 1.0

    consumption = result["evaluation"]["metrics"][
        "water_consumption"
    ]

    assert consumption["actual_conflict_flag"] is False
    assert consumption["conflict_correct"] is True
    assert consumption["actual_review_required"] is False
    assert consumption["review_correct"] is True

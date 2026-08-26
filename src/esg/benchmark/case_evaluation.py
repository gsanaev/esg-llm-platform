from __future__ import annotations

from typing import Any, Mapping

from esg.benchmark.evaluation import evaluate_normalized_predictions
from esg.benchmark.runner import run_benchmark_method


def _get_truth_company(
    truth: Mapping[str, Any],
    company_id: str,
) -> Mapping[str, Any]:
    """Return one benchmark company from hidden truth."""
    companies = truth.get("companies") or []

    for company in companies:
        if str(company.get("company_id")) == company_id:
            return company

    raise ValueError(
        f"Unknown benchmark company_id: {company_id}"
    )


def evaluate_benchmark_case(
    pdf_path: str,
    *,
    case: Mapping[str, Any],
    truth: Mapping[str, Any],
    method: str,
    kpi_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Run one extraction method on one benchmark case and evaluate it
    against the matching hidden-truth company.

    This function performs orchestration only. It does not modify
    extraction, normalization, reconciliation, or evaluation semantics.
    """
    case_id = str(case["case_id"])
    company_id = str(case["company_id"])

    company = _get_truth_company(
        truth,
        company_id,
    )

    truth_metrics = company.get("metrics") or {}

    predictions = run_benchmark_method(
        pdf_path,
        method=method,
        kpi_schema=kpi_schema,
    )

    evaluation = evaluate_normalized_predictions(
        truth_metrics,
        predictions,
        expected_location=company.get("facility_location"),
    )

    return {
        "case_id": case_id,
        "company_id": company_id,
        "method": method,
        "predictions": predictions,
        "evaluation": evaluation,
    }

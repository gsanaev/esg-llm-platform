from __future__ import annotations

from typing import Any, Mapping

from esg.benchmark.workflow_evaluation import (
    evaluate_reconciled_results,
)
from esg.pipeline.pipeline import ESGPipelineV2


def evaluate_benchmark_workflow_case(
    pdf_path: str,
    *,
    case: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Run the reconciled workflow on one benchmark case and evaluate
    its final decisions against explicit case-level expectations.
    """
    case_id = str(case["case_id"])

    expected_reconciliation = (
        case.get("expected_reconciliation") or {}
    )

    if not expected_reconciliation:
        raise ValueError(
            "Benchmark workflow case has no "
            f"expected_reconciliation: {case_id}"
        )

    pipeline = ESGPipelineV2()

    reconciled = pipeline.run_on_pdf_reconciled(
        pdf_path
    )

    evaluation = evaluate_reconciled_results(
        expected_reconciliation,
        reconciled,
    )

    return {
        "case_id": case_id,
        "results": reconciled,
        "evaluation": evaluation,
    }

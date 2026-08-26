from esg.benchmark.workflow_evaluation import (
    evaluate_reconciled_results,
)
from esg.core.types import ReconciledKPIResult


def test_evaluate_reconciled_results_scores_conflict_and_review_flags():
    expected = {
        "water_withdrawal": {
            "conflict_flag": True,
            "review_required": True,
            "status": "review_required",
        },
        "water_consumption": {
            "conflict_flag": False,
            "review_required": False,
            "status": "not_reported",
        },
    }

    results = [
        ReconciledKPIResult(
            metric="water_withdrawal",
            value=None,
            unit="m3",
            conflict_flag=True,
            review_required=True,
            status="review_required",
        ),
        ReconciledKPIResult(
            metric="water_consumption",
            value=None,
            unit=None,
            conflict_flag=False,
            review_required=False,
            status="not_reported",
        ),
    ]

    evaluation = evaluate_reconciled_results(
        expected,
        results,
    )

    summary = evaluation["summary"]

    assert summary["conflict_detection_accuracy"] == 1.0
    assert summary["review_flag_accuracy"] == 1.0

    withdrawal = evaluation["metrics"]["water_withdrawal"]

    assert withdrawal["conflict_correct"] is True
    assert withdrawal["review_correct"] is True

    consumption = evaluation["metrics"]["water_consumption"]

    assert consumption["conflict_correct"] is True
    assert consumption["review_correct"] is True

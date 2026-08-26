from __future__ import annotations

from typing import Any, Mapping, Sequence

from esg.core.types import ReconciledKPIResult


def _safe_ratio(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def evaluate_reconciled_results(
    expected_reconciliation: Mapping[
        str,
        Mapping[str, Any],
    ],
    results: Sequence[ReconciledKPIResult],
) -> dict[str, Any]:
    """
    Evaluate reconciled workflow outputs against case-level expectations.

    This evaluator is independent from PDF extraction and reconciliation.
    It scores only the final workflow decisions supplied by the caller.
    """
    by_metric = {
        result.metric: result
        for result in results
    }

    metric_results: dict[str, dict[str, Any]] = {}

    conflict_comparisons = 0
    conflict_correct_count = 0

    review_comparisons = 0
    review_correct_count = 0

    for metric in sorted(expected_reconciliation):
        expected = expected_reconciliation[metric]
        actual = by_metric.get(metric)

        expected_conflict = bool(
            expected.get("conflict_flag", False)
        )
        expected_review = bool(
            expected.get("review_required", False)
        )

        actual_conflict = (
            actual.conflict_flag
            if actual is not None
            else None
        )
        actual_review = (
            actual.review_required
            if actual is not None
            else None
        )

        conflict_correct = (
            actual_conflict == expected_conflict
        )
        review_correct = (
            actual_review == expected_review
        )

        conflict_comparisons += 1
        review_comparisons += 1

        if conflict_correct:
            conflict_correct_count += 1

        if review_correct:
            review_correct_count += 1

        metric_results[metric] = {
            "expected_conflict_flag": expected_conflict,
            "actual_conflict_flag": actual_conflict,
            "conflict_correct": conflict_correct,
            "expected_review_required": expected_review,
            "actual_review_required": actual_review,
            "review_correct": review_correct,
        }

    summary = {
        "conflict_detection_accuracy": _safe_ratio(
            conflict_correct_count,
            conflict_comparisons,
        ),
        "review_flag_accuracy": _safe_ratio(
            review_correct_count,
            review_comparisons,
        ),
    }

    return {
        "metrics": metric_results,
        "summary": summary,
    }

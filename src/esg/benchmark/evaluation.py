from __future__ import annotations

from math import isclose
from typing import Any, Mapping


def _is_numeric(value: Any) -> bool:
    """Return True for benchmark numeric values, excluding booleans."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def _values_equal(
    expected: Any,
    predicted: Any,
) -> bool:
    """Compare normalized benchmark values."""
    if _is_numeric(expected) and _is_numeric(predicted):
        return isclose(
            float(expected),
            float(predicted),
            rel_tol=1e-9,
            abs_tol=1e-9,
        )

    return expected == predicted


def _safe_ratio(
    numerator: int,
    denominator: int,
) -> float:
    """
    Return a deterministic benchmark ratio.

    A zero denominator is treated as zero rather than producing
    NaN or an exception.
    """
    if denominator == 0:
        return 0.0

    return numerator / denominator


def evaluate_normalized_predictions(
    truth_metrics: Mapping[str, Mapping[str, Any]],
    predictions: Mapping[str, Mapping[str, Any]],
    *,
    expected_location: str | None = None,
    expected_year: int | None = None,
) -> dict[str, Any]:
    """
    Compare normalized method predictions with hidden benchmark truth.

    This function is deliberately independent from PDF extraction,
    reconciliation, heuristic extraction scores, and LLM execution.

    Detection metrics operate on non-missing values.

    Value and unit accuracy are evaluated only where the expected metric
    was actually detected. Missing detections are accounted for separately
    through detection recall and extraction coverage.
    """
    metric_codes = set(truth_metrics) | set(predictions)

    metric_results: dict[str, dict[str, Any]] = {}

    true_positives = 0
    predicted_positives = 0
    expected_positives = 0

    numeric_comparisons = 0
    numeric_correct = 0

    unit_comparisons = 0
    unit_correct_count = 0
    location_comparisons = 0
    location_correct_count = 0
    year_comparisons = 0
    year_correct_count = 0

    for code in sorted(metric_codes):
        truth_entry = truth_metrics.get(code) or {}
        prediction_entry = predictions.get(code) or {}

        expected_value = truth_entry.get("value")
        predicted_value = prediction_entry.get("value")

        expected_unit = truth_entry.get("unit")
        predicted_unit = prediction_entry.get("unit")
        predicted_location = prediction_entry.get("location")
        predicted_year = prediction_entry.get("year")

        expected_present = expected_value is not None
        predicted_present = predicted_value is not None

        if expected_present:
            expected_positives += 1

        if predicted_present:
            predicted_positives += 1

        if expected_present and predicted_present:
            true_positives += 1

        value_correct = (
            expected_present
            and predicted_present
            and _values_equal(
                expected_value,
                predicted_value,
            )
        )

        unit_correct = (
            expected_present
            and predicted_present
            and expected_unit == predicted_unit
        )

        location_correct = (
            expected_present
            and predicted_present
            and expected_location is not None
            and predicted_location == expected_location
        )

        year_correct = (
            expected_present
            and predicted_present
            and expected_year is not None
            and predicted_year == expected_year
        )

        if (
            expected_present
            and predicted_present
            and _is_numeric(expected_value)
        ):
            numeric_comparisons += 1

            if value_correct:
                numeric_correct += 1

        if (
            expected_present
            and predicted_present
            and expected_unit is not None
        ):
            unit_comparisons += 1

            if unit_correct:
                unit_correct_count += 1

        if (
            expected_present
            and predicted_present
            and expected_location is not None
        ):
            location_comparisons += 1

            if location_correct:
                location_correct_count += 1

        if (
            expected_present
            and predicted_present
            and expected_year is not None
        ):
            year_comparisons += 1

            if year_correct:
                year_correct_count += 1

        metric_results[code] = {
            "expected_present": expected_present,
            "predicted_present": predicted_present,
            "value_correct": value_correct,
            "unit_correct": unit_correct,
            "location_correct": location_correct,
            "year_correct": year_correct,
        }

    summary = {
        "detection_precision": _safe_ratio(
            true_positives,
            predicted_positives,
        ),
        "detection_recall": _safe_ratio(
            true_positives,
            expected_positives,
        ),
        "numeric_value_accuracy": _safe_ratio(
            numeric_correct,
            numeric_comparisons,
        ),
        "unit_accuracy": _safe_ratio(
            unit_correct_count,
            unit_comparisons,
        ),
        "location_accuracy": _safe_ratio(
            location_correct_count,
            location_comparisons,
        ),
        "extraction_coverage": _safe_ratio(
            true_positives,
            expected_positives,
        ),
        "reporting_year_accuracy": _safe_ratio(
            year_correct_count,
            year_comparisons,
        ),
    }

    return {
        "metrics": metric_results,
        "summary": summary,
    }

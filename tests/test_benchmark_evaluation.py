from esg.benchmark.evaluation import evaluate_normalized_predictions


def test_evaluate_normalized_predictions_perfect_match():
    truth = {
        "water_withdrawal": {
            "value": 1_200_000.0,
            "unit": "m3",
        },
        "water_stress_share": {
            "value": 0.38,
            "unit": "fraction",
        },
        "water_dependency": {
            "value": "high dependency",
            "unit": None,
        },
    }

    predictions = {
        "water_withdrawal": {
            "value": 1_200_000.0,
            "unit": "m3",
        },
        "water_stress_share": {
            "value": 0.38,
            "unit": "fraction",
        },
        "water_dependency": {
            "value": "high dependency",
            "unit": None,
        },
    }

    evaluation = evaluate_normalized_predictions(
        truth,
        predictions,
    )

    assert evaluation["summary"]["detection_precision"] == 1.0
    assert evaluation["summary"]["detection_recall"] == 1.0
    assert evaluation["summary"]["numeric_value_accuracy"] == 1.0
    assert evaluation["summary"]["unit_accuracy"] == 1.0
    assert evaluation["summary"]["extraction_coverage"] == 1.0

    dependency = evaluation["metrics"]["water_dependency"]

    assert dependency["expected_present"] is True
    assert dependency["predicted_present"] is True
    assert dependency["value_correct"] is True
    assert dependency["unit_correct"] is True


def test_evaluate_normalized_predictions_detects_errors_and_missingness():
    truth = {
        "water_withdrawal": {
            "value": 1_200_000.0,
            "unit": "m3",
        },
        "water_stress_share": {
            "value": 0.38,
            "unit": "fraction",
        },
        "water_dependency": {
            "value": "high dependency",
            "unit": None,
        },
    }

    predictions = {
        "water_withdrawal": {
            "value": 1_200_000.0,
            "unit": "m3",
        },
        "water_stress_share": {
            "value": 0.40,
            "unit": "fraction",
        },
        "energy_consumption": {
            "value": 500_000.0,
            "unit": "MWh",
        },
    }

    evaluation = evaluate_normalized_predictions(
        truth,
        predictions,
    )

    summary = evaluation["summary"]

    assert summary["detection_precision"] == 2 / 3
    assert summary["detection_recall"] == 2 / 3
    assert summary["numeric_value_accuracy"] == 0.5
    assert summary["unit_accuracy"] == 1.0
    assert summary["extraction_coverage"] == 2 / 3

    withdrawal = evaluation["metrics"]["water_withdrawal"]
    assert withdrawal["value_correct"] is True
    assert withdrawal["unit_correct"] is True

    stress = evaluation["metrics"]["water_stress_share"]
    assert stress["value_correct"] is False
    assert stress["unit_correct"] is True

    dependency = evaluation["metrics"]["water_dependency"]
    assert dependency["expected_present"] is True
    assert dependency["predicted_present"] is False
    assert dependency["value_correct"] is False

    false_positive = evaluation["metrics"]["energy_consumption"]
    assert false_positive["expected_present"] is False
    assert false_positive["predicted_present"] is True


def test_evaluate_normalized_predictions_penalizes_false_missing_value():
    truth = {
        "water_consumption": {
            "value": 800_000.0,
            "unit": "m3",
        },
    }

    predictions = {
        "water_consumption": {
            "value": 800_000.0,
            "unit": "m3",
        },
    }

    evaluation = evaluate_normalized_predictions(
        truth,
        predictions,
        expected_missing_metrics={
            "water_consumption",
        },
    )

    summary = evaluation["summary"]
    consumption = evaluation["metrics"][
        "water_consumption"
    ]

    assert summary["missing_value_accuracy"] == 0.0
    assert consumption["expected_present"] is False
    assert consumption["expected_missing"] is True
    assert consumption["predicted_present"] is True
    assert consumption["missing_value_correct"] is False

    assert summary["detection_precision"] == 0.0

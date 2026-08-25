from pathlib import Path

from esg.benchmark.truth import load_benchmark_truth


TRUTH_PATH = Path("data/benchmark/truth/benchmark_truth.yaml")


def test_load_benchmark_truth():
    truth = load_benchmark_truth(TRUTH_PATH)

    assert truth["benchmark_version"] == "2.0"
    assert len(truth["companies"]) == 2

    alpha = truth["companies"][0]

    assert alpha["company_id"] == "synthetic_alpha"
    assert alpha["reporting_year"] == 2024
    assert alpha["metrics"]["total_ghg_emissions"] == {
        "value": 123400.0,
        "unit": "tCO2e",
    }
    assert alpha["metrics"]["energy_consumption"] == {
        "value": 500000.0,
        "unit": "MWh",
    }
    assert alpha["metrics"]["water_withdrawal"] == {
        "value": 1200000.0,
        "unit": "m3",
    }
    assert alpha["metrics"]["water_consumption"] == {
        "value": 800000.0,
        "unit": "m3",
    }
    assert alpha["metrics"]["water_stress_share"] == {
        "value": 0.38,
        "unit": "fraction",
    }
    assert alpha["metrics"]["water_dependency"] == {
        "value": "high dependency",
        "unit": None,
    }

    beta = truth["companies"][1]

    assert beta["company_id"] == "synthetic_beta"
    assert beta["metrics"]["water_consumption"] == {
        "value": 510000.0,
        "unit": "m3",
    }
    assert beta["metrics"]["water_stress_share"] == {
        "value": 0.62,
        "unit": "fraction",
    }
    assert beta["metrics"]["water_dependency"] == {
        "value": "moderate dependency",
        "unit": None,
    }

from pathlib import Path

from esg.benchmark.cases import load_benchmark_cases


CASES_PATH = Path("data/benchmark/cases/benchmark_cases.yaml")


def test_load_benchmark_cases():
    cases = load_benchmark_cases(CASES_PATH)

    assert len(cases) == 6

    assert [case["case_id"] for case in cases] == [
        "alpha_structured_table",
        "alpha_clean_narrative",
        "beta_locale_table",
        "beta_mixed_units",
        "alpha_missing_water_consumption",
        "alpha_conflicting_water_withdrawal",
    ]

    mixed_units = cases[3]

    assert mixed_units["company_id"] == "synthetic_beta"
    assert mixed_units["disclosure_format"] == "table"
    assert mixed_units["unit_overrides"] == {
        "energy_consumption": "GWh",
    }

    missing = cases[4]

    assert missing["company_id"] == "synthetic_alpha"
    assert missing["disclosure_format"] == "table"
    assert missing["omitted_metrics"] == [
        "water_consumption",
    ]
    assert missing["expected_reconciliation"] == {
        "water_consumption": {
            "conflict_flag": False,
            "review_required": False,
            "status": "not_reported",
        },
    }

    conflict = cases[5]

    assert conflict["company_id"] == "synthetic_alpha"
    assert conflict["disclosure_format"] == "table"
    assert conflict["conflicting_values"] == {
        "water_withdrawal": [
            1250000,
        ],
    }
    assert conflict["expected_reconciliation"] == {
        "water_withdrawal": {
            "conflict_flag": True,
            "review_required": True,
            "status": "review_required",
        },
    }

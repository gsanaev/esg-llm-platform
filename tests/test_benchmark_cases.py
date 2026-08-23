from pathlib import Path

from esg.benchmark.cases import load_benchmark_cases


CASES_PATH = Path("data/benchmark/cases/benchmark_cases.yaml")


def test_load_benchmark_cases():
    cases = load_benchmark_cases(CASES_PATH)

    assert len(cases) == 4

    assert [case["case_id"] for case in cases] == [
        "alpha_structured_table",
        "alpha_clean_narrative",
        "beta_locale_table",
        "beta_mixed_units",
    ]

    mixed_units = cases[3]

    assert mixed_units["company_id"] == "synthetic_beta"
    assert mixed_units["disclosure_format"] == "table"
    assert mixed_units["unit_overrides"] == {
        "energy_consumption": "GWh",
    }

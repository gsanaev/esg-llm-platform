# tests/test_regex.py
import json
from pathlib import Path

from esg.extractors.regex_extractor import (
    extract_kpi_candidates_regex,
    extract_kpis_regex,
)
from esg.normalization.regex_normalizer import normalize_regex_result
from esg.utils.pdf_reader import extract_text


SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/samples/esg_simple_text.pdf")   # updated


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_regex_basic_extraction():
    kpi_schema = load_kpis()
    text = extract_text(str(PDF_PATH))

    raw = extract_kpis_regex(text, kpi_schema)
    normalized = normalize_regex_result(raw, kpi_schema)

    assert isinstance(normalized, dict)

    for code, result in normalized.items():
        assert "value" in result
        assert isinstance(result["value"], (float, type(None)))
        assert "unit" in result


def test_regex_preserves_multiple_candidates():
    kpi_schema = load_kpis()

    text = (
        "Water withdrawal was 1,200,000 m3. "
        "Later water withdrawal was 1,250,000 m3."
    )

    candidates = extract_kpi_candidates_regex(
        text,
        kpi_schema,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 2
    assert [entry["raw_value"] for entry in water] == [
        "1,200,000",
        "1,250,000",
    ]
    assert all(entry["raw_unit"] == "m3" for entry in water)

    single_result = extract_kpis_regex(
        text,
        kpi_schema,
    )

    assert single_result["water_withdrawal"]["raw_value"] == "1,200,000"


def test_regex_candidates_deduplicate_overlapping_patterns():
    kpi_schema = load_kpis()

    text = "Water withdrawal (m3) 1,200,000."

    candidates = extract_kpi_candidates_regex(
        text,
        kpi_schema,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 1
    assert water[0]["raw_value"] == "1,200,000"
    assert water[0]["raw_unit"] == "m3"


def test_regex_distinguishes_water_withdrawal_from_consumption():
    kpi_schema = load_kpis()

    text = (
        "Total water withdrawal was 1,200,000 m3. "
        "Total water consumption was 800,000 m3."
    )

    candidates = extract_kpi_candidates_regex(
        text,
        kpi_schema,
    )

    assert [
        entry["raw_value"]
        for entry in candidates["water_withdrawal"]
    ] == ["1,200,000"]

    assert [
        entry["raw_value"]
        for entry in candidates["water_consumption"]
    ] == ["800,000"]

    single_result = extract_kpis_regex(
        text,
        kpi_schema,
    )

    assert single_result["water_withdrawal"]["raw_value"] == "1,200,000"
    assert single_result["water_consumption"]["raw_value"] == "800,000"


def test_regex_shared_unit_does_not_use_stale_metric_context():
    kpi_schema = load_kpis()

    text = (
        "Water withdrawal was discussed earlier. "
        + ("Background context without KPI information. " * 10)
        + "800,000 m3."
    )

    candidates = extract_kpi_candidates_regex(
        text,
        kpi_schema,
    )

    assert "water_withdrawal" not in candidates
    assert "water_consumption" not in candidates

    single_result = extract_kpis_regex(
        text,
        kpi_schema,
    )

    assert "water_withdrawal" not in single_result
    assert "water_consumption" not in single_result


def test_regex_percentage_metric_requires_local_semantic_context():
    kpi_schema = load_kpis()

    unrelated_text = (
        "Renewable electricity increased to 38%."
    )

    unrelated = extract_kpi_candidates_regex(
        unrelated_text,
        kpi_schema,
    )

    assert "water_stress_share" not in unrelated

    relevant_text = (
        "Share of water use in water-stressed areas was 38%."
    )

    relevant = extract_kpi_candidates_regex(
        relevant_text,
        kpi_schema,
    )

    water_stress = relevant["water_stress_share"]

    assert len(water_stress) == 1
    assert water_stress[0]["raw_value"] == "38"
    assert water_stress[0]["raw_unit"] == "%"
    unrelated_single_result = extract_kpis_regex(
        unrelated_text,
        kpi_schema,
    )

    assert "water_stress_share" not in unrelated_single_result

    relevant_single_result = extract_kpis_regex(
        relevant_text,
        kpi_schema,
    )

    assert relevant_single_result["water_stress_share"]["raw_value"] == "38"
    assert relevant_single_result["water_stress_share"]["raw_unit"] == "%"

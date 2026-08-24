# tests/test_nlp.py
import json
from pathlib import Path

from esg.extractors.nlp_extractor import (
    extract_kpi_candidates_nlp,
    extract_kpis_nlp,
)
from esg.normalization.nlp_normalizer import normalize_nlp_result
from esg.utils.pdf_reader import extract_text


SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")
PDF_PATH = Path("data/samples/esg_nlp_test.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_nlp_extractor_on_esg_report_v1():
    kpis = load_kpis()
    text = extract_text(str(PDF_PATH))

    raw = extract_kpis_nlp(text, kpis)
    normalized = normalize_nlp_result(raw, kpis)

    assert "total_ghg_emissions" in normalized
    assert "energy_consumption" in normalized
    assert "water_withdrawal" in normalized

    ghg = normalized["total_ghg_emissions"]
    energy = normalized["energy_consumption"]
    water = normalized["water_withdrawal"]

    assert ghg["value"] == 123400.0
    assert ghg["unit"] in ("tCO2e", "tco2e")

    assert energy["value"] == 500000.0
    assert energy["unit"].lower() == "mwh"

    assert water["value"] == 1200000.0
    assert water["unit"].lower() in ("m3", "m³")


def test_nlp_preserves_multiple_candidates():
    kpis = load_kpis()

    text = (
        "Water withdrawal was 1,200,000 m3. "
        "Water withdrawal was 1,250,000 m3."
    )

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 2
    assert [entry["raw_value"] for entry in water] == [
        "1,200,000",
        "1,250,000",
    ]
    assert all(entry["raw_unit"] == "m3" for entry in water)

    legacy = extract_kpis_nlp(
        text,
        kpis,
    )

    assert legacy["water_withdrawal"]["raw_value"] == "1,200,000"


def test_nlp_candidates_deduplicate_overlapping_windows():
    kpis = load_kpis()

    text = (
        "Water withdrawal is reported below. "
        "Water withdrawal was 1,200,000 m3."
    )

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 1
    assert water[0]["raw_value"] == "1,200,000"
    assert water[0]["raw_unit"] == "m3"


def test_nlp_candidates_reject_weak_match_with_trailing_comma():
    kpis = load_kpis()

    text = "Water withdrawal (m3) was 500,000,"

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    assert "water_withdrawal" not in candidates


def test_nlp_candidates_skip_ambiguous_multi_value_weak_window():
    kpis = load_kpis()

    text = (
        "Total GHG emissions tCO2e 123,400 "
        "Total energy consumption MWh 500,000 "
        "Total water withdrawal m3 1,200,000"
    )

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    assert candidates == {}


def test_nlp_candidates_preserve_single_unambiguous_weak_match():
    kpis = load_kpis()

    text = "Water withdrawal (m3) was 500,000"

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    water = candidates["water_withdrawal"]

    assert len(water) == 1
    assert water[0]["raw_value"] == "500,000"
    assert water[0]["raw_unit"] is None


def test_nlp_distinguishes_water_withdrawal_from_consumption():
    kpis = load_kpis()

    kpis["water_consumption"] = {
        "display_name": "Water Consumption",
        "value_type": "quantitative",
        "canonical_unit": "m3",
        "accepted_units": ["m3", "m³", "cubic meters"],
        "synonyms": [
            "water consumption",
            "total water consumption",
        ],
        "keywords": [
            "water consumption",
            "water consumed",
        ],
    }

    text = (
        "Total water withdrawal was 1,200,000 m3. "
        "Total water consumption was 800,000 m3."
    )

    candidates = extract_kpi_candidates_nlp(
        text,
        kpis,
    )

    assert [
        entry["raw_value"]
        for entry in candidates["water_withdrawal"]
    ] == ["1,200,000"]

    assert [
        entry["raw_value"]
        for entry in candidates["water_consumption"]
    ] == ["800,000"]

    legacy = extract_kpis_nlp(
        text,
        kpis,
    )

    assert legacy["water_withdrawal"]["raw_value"] == "1,200,000"
    assert legacy["water_consumption"]["raw_value"] == "800,000"

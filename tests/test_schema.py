import json
from pathlib import Path

SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")

from esg.core.schema import (
    get_accepted_units,
    get_canonical_unit,
    get_synonyms,
)


def test_schema_helpers_support_legacy_units():
    meta = {
        "units": ["MWh", "kWh", "GWh"],
    }

    assert get_accepted_units(meta) == ["MWh", "kWh", "GWh"]
    assert get_canonical_unit(meta) == "MWh"


def test_schema_helpers_prefer_v2_unit_fields():
    meta = {
        "canonical_unit": "m3",
        "accepted_units": ["m3", "m³", "cubic meters"],
        "units": ["legacy-unit"],
    }

    assert get_accepted_units(meta) == ["m3", "m³", "cubic meters"]
    assert get_canonical_unit(meta) == "m3"


def test_schema_helpers_prefer_explicit_synonyms():
    meta = {
        "synonyms": ["water withdrawal", "total water withdrawal"],
        "keywords": ["water use"],
    }

    assert get_synonyms("water_withdrawal", meta) == [
        "water withdrawal",
        "total water withdrawal",
    ]


def test_schema_helpers_do_not_treat_keywords_as_synonyms():
    meta = {
        "keywords": ["water use", "water extracted"],
    }

    assert get_synonyms("water_withdrawal", meta) == [
        "water withdrawal"
    ]


def test_schema_helpers_fall_back_to_metric_code():
    assert get_synonyms("water_withdrawal", {}) == ["water withdrawal"]


def test_universal_kpi_schema_has_explicit_v2_contract():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert set(schema) == {
        "total_ghg_emissions",
        "energy_consumption",
        "water_withdrawal",
        "water_consumption",
        "water_stress_share",
    }

    for code, meta in schema.items():
        assert meta["value_type"] == "quantitative"
        assert meta["canonical_unit"]
        assert meta["canonical_unit"] in meta["accepted_units"]
        assert meta["accepted_units"]
        assert meta["synonyms"]
        assert meta["keywords"]

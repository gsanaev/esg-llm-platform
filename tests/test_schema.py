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
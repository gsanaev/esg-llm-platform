import pytest

from esg.normalization.nlp_normalizer import normalize_nlp_result
from esg.normalization.regex_normalizer import normalize_regex_result
from esg.normalization.table_grid_normalizer import (
    normalize_table_grid_result,
)
from esg.normalization.table_plain_normalizer import (
    normalize_table_plain_result,
)


WATER_STRESS_SCHEMA = {
    "water_stress_share": {
        "display_name": "Water Stress Share",
        "value_type": "quantitative",
        "canonical_unit": "fraction",
        "accepted_units": [
            "fraction",
            "%",
            "percent",
            "percentage",
        ],
        "synonyms": [
            "water stress share",
            "share in water-stressed areas",
            "share of water use in water-stressed areas",
        ],
        "keywords": [
            "water stress",
            "water-stressed areas",
        ],
        "requires_metric_context": True,
    }
}


NORMALIZERS = [
    normalize_regex_result,
    normalize_nlp_result,
    normalize_table_grid_result,
    normalize_table_plain_result,
]


@pytest.mark.parametrize("normalizer", NORMALIZERS)
def test_percentage_share_normalizes_to_fraction(normalizer):
    raw = {
        "water_stress_share": {
            "raw_value": "38",
            "raw_unit": "%",
            "confidence": 0.8,
        }
    }

    normalized = normalizer(
        raw,
        WATER_STRESS_SCHEMA,
    )

    result = normalized["water_stress_share"]

    assert result["value"] == pytest.approx(0.38)
    assert result["unit"] == "fraction"


@pytest.mark.parametrize("normalizer", NORMALIZERS)
def test_fraction_share_is_not_rescaled(normalizer):
    raw = {
        "water_stress_share": {
            "raw_value": "0.38",
            "raw_unit": "fraction",
            "confidence": 0.8,
        }
    }

    normalized = normalizer(
        raw,
        WATER_STRESS_SCHEMA,
    )

    result = normalized["water_stress_share"]

    assert result["value"] == pytest.approx(0.38)
    assert result["unit"] == "fraction"

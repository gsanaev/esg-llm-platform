# tests/test_llm.py
import json
from pathlib import Path
from unittest.mock import patch

from esg.extractors.llm_extractor import extract_kpis_llm
from esg.normalization.llm_normalizer import normalize_llm_result

import os

SCHEMA_PATH = Path("src/esg/schemas/universal_kpis.json")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


MOCK_RESPONSE = {
    "total_ghg_emissions": {"raw_value": "123,400", "raw_unit": "tCO2e"},
    "energy_consumption": {"raw_value": "500,000", "raw_unit": "MWh"},
    "water_withdrawal": {"raw_value": "1,200,000", "raw_unit": "m3"},
}


class MockChoice:
    def __init__(self):
        self.message = type("m", (), {"content": json.dumps(MOCK_RESPONSE)})


class MockCompletion:
    choices = [MockChoice()]


def mock_create(*args, **kwargs):
    return MockCompletion()


@patch.dict(os.environ, {"OPENAI_API_KEY": "dummy"})
@patch("openai.resources.chat.completions.Completions.create", new=mock_create)
def test_llm_extractor_and_normalizer():
    kpis = load_kpis()

    raw = extract_kpis_llm("dummy text", kpis)
    norm = normalize_llm_result(raw, kpis)

    assert norm["total_ghg_emissions"]["value"] == 123400.0
    assert norm["total_ghg_emissions"]["unit"] == "tCO2e"


@patch.dict(os.environ, {"OPENAI_API_KEY": "dummy"})
@patch("openai.resources.chat.completions.Completions.create")
def test_llm_prompt_is_schema_guided(mock_create):
    mock_create.return_value = MockCompletion()

    kpis = load_kpis()

    extract_kpis_llm(
        "dummy text",
        kpis,
    )

    request = mock_create.call_args.kwargs
    system_prompt = request["messages"][0]["content"]

    for code in kpis:
        assert code in system_prompt

    assert "water_consumption" in system_prompt
    assert "water_stress_share" in system_prompt
    assert "water_dependency" in system_prompt

    assert "fraction" in system_prompt
    assert "qualitative" in system_prompt.lower()


@patch.dict(os.environ, {"OPENAI_API_KEY": "dummy"})
@patch("openai.resources.chat.completions.Completions.create")
def test_llm_prompt_respects_schema_subset(mock_create):
    mock_create.return_value = MockCompletion()

    kpis = load_kpis()

    subset = {
        code: kpis[code]
        for code in [
            "water_consumption",
            "water_dependency",
        ]
    }

    extract_kpis_llm(
        "dummy text",
        subset,
    )

    request = mock_create.call_args.kwargs
    system_prompt = request["messages"][0]["content"]

    assert "water_consumption" in system_prompt
    assert "water_dependency" in system_prompt

    assert "total_ghg_emissions" not in system_prompt
    assert "energy_consumption" not in system_prompt
    assert "water_withdrawal" not in system_prompt
    assert "water_stress_share" not in system_prompt


def test_llm_normalizer_supports_share_and_qualitative_values():
    kpis = load_kpis()

    raw = {
        "water_consumption": {
            "raw_value": "800,000",
            "raw_unit": "m3",
            "confidence": 0.75,
        },
        "water_stress_share": {
            "raw_value": "38",
            "raw_unit": "%",
            "confidence": 0.75,
        },
        "water_dependency": {
            "raw_value": "High dependency",
            "raw_unit": None,
            "confidence": 0.75,
        },
    }

    normalized = normalize_llm_result(
        raw,
        kpis,
    )

    consumption = normalized["water_consumption"]
    assert consumption["value"] == 800_000.0
    assert consumption["unit"] == "m3"

    stress = normalized["water_stress_share"]
    assert stress["value"] == 0.38
    assert stress["unit"] == "fraction"

    dependency = normalized["water_dependency"]
    assert dependency["value"] == "high dependency"
    assert dependency["unit"] is None

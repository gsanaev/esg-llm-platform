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

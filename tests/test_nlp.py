# tests/test_nlp.py
import json
from pathlib import Path

from esg_v2.extractors.nlp_extractor_v2 import extract_kpis_nlp_v2
from esg_v2.normalization.regex_normalizer import normalize_regex_result_v2
from esg_system.core.pdf_reader import extract_text


SCHEMA_PATH = Path("src/esg_system/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/esg_report_v1.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_nlp_extractor_on_esg_report_v1():
    kpis = load_kpis()
    text = extract_text(str(PDF_PATH))

    raw = extract_kpis_nlp_v2(text, kpis)
    normalized = normalize_regex_result_v2(raw, kpis)

    # We expect at least the three core KPIs to be found
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
    # normalize_regex_result_v2 uses "m3" as canonical
    assert water["unit"].lower() in ("m3", "m³")

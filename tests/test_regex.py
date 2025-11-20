# tests/test_regex.py
import json
from pathlib import Path

from esg.extractors.regex_extractor import extract_kpis_regex
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

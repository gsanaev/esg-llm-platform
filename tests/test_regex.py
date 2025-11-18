# src/esg_v2/tests/test_regex.py

import json
from pathlib import Path

from esg_v2.extractors.regex_extractor_v2 import extract_kpis_regex_v2
from esg_v2.normalization.regex_normalizer import normalize_regex_result_v2
from esg_system.core.pdf_reader import extract_text


SCHEMA_PATH = Path("src/esg_system/schemas/universal_kpis.json")
PDF_PATH = Path("data/raw/esg_report_v1.pdf")


def load_kpis():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_regex_basic_extraction():
    kpi_schema = load_kpis()
    text = extract_text(str(PDF_PATH))

    raw = extract_kpis_regex_v2(text, kpi_schema)
    normalized = normalize_regex_result_v2(raw, kpi_schema)

    # Basic structure checks
    assert isinstance(normalized, dict)

    for code, result in normalized.items():
        # Value field should exist
        assert "value" in result

        # If extraction exists → value must be a float or None
        assert isinstance(result["value"], (float, type(None)))

        # Unit field should exist (may be None if PDF has no matching unit)
        assert "unit" in result

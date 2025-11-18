# src/esg_v2/extractors/llm_extractor_v2.py
from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

from openai import OpenAI

import os

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an ESG data extraction model.
You must extract ONLY these KPI values if present in the text:

- total_ghg_emissions (unit: tCO2e)
- energy_consumption (unit: MWh)
- water_withdrawal   (unit: m3)

Rules:
- Return a JSON object with exactly these keys (even if missing):
  {
    "<kpi_code>": { "raw_value": str|None, "raw_unit": str|None }
  }
- Extract only the FIRST occurrence.
- Keep raw_value exactly as seen in the text (e.g. "123,400", "1.2 million").
- Keep raw_unit exactly as seen (e.g. "tCO2e", "MWh", "m³").
- If KPI not found, return: { "raw_value": null, "raw_unit": null }.
"""


def extract_kpis_llm_v2(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    model: str = "gpt-4o-mini",
    base_confidence: float = 0.75,
) -> Dict[str, Dict[str, Any]]:
    """
    LLM-based KPI extractor compatible with normalization/regex/table.
    Returns shape:
       {
          code: {
             "raw_value": str or None,
             "raw_unit":  str or None,
             "confidence": float
          }
       }
    """

    # If no API key, disable LLM extractor for tests
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("LLM extractor disabled (no OPENAI_API_KEY set).")
        return {}

    client = OpenAI()

    logger.info("llm_v2: querying model=%s", model)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=300,
        )
    except Exception as e:
        logger.error("llm_v2: API error: %s", e)
        return {}

    content = completion.choices[0].message.content

    # Try to parse JSON
    import json

    try:
        data = json.loads(content)
    except Exception as e:
        logger.error("llm_v2: failed to parse JSON: %s", e)
        return {}

    out: Dict[str, Dict[str, Any]] = {}

    for code in kpi_schema.keys():
        entry = data.get(code, {}) or {}
        raw_value = entry.get("raw_value")
        raw_unit = entry.get("raw_unit")

        if raw_value is None:
            continue

        out[code] = {
            "raw_value": raw_value,
            "raw_unit": raw_unit,
            "confidence": base_confidence,
        }

    return out

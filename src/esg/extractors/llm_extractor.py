# src/esg/extractors/llm_extractor.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Mapping

from openai import OpenAI

logger = logging.getLogger(__name__)

# ======================================================================
# System prompt
# ======================================================================

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


# ======================================================================
# Public LLM extractor
# ======================================================================

def extract_kpis_llm(
    text: str,
    kpi_schema: Mapping[str, Any],
    *,
    model: str = "gpt-4o-mini",
    base_confidence: float = 0.75,
) -> Dict[str, Dict[str, Any]]:
    """
    LLM-based KPI extractor.
    Returns same structure as regex/table/nlp extractors:
        { code: { raw_value, raw_unit, confidence } }
    """

    # ------------------------------------------------------------------
    # 0) Check for API key (.env should load it)
    # ------------------------------------------------------------------
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("llm: extractor disabled (missing OPENAI_API_KEY).")
        return {}

    client = OpenAI(api_key=api_key)
    logger.info("llm: querying model %s", model)

    # ------------------------------------------------------------------
    # 1) Query model
    # ------------------------------------------------------------------
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
    except Exception as exc:
        logger.error("llm: API error: %s", exc)
        return {}

    # ------------------------------------------------------------------
    # 2) Extract text response
    # ------------------------------------------------------------------
    try:
        content = completion.choices[0].message.content
    except Exception:
        logger.error("llm: invalid API response structure")
        return {}

    if not content:
        logger.error("llm: empty response from model")
        return {}

    # Unwrap ```json ... ```
    cleaned = (
        content.strip()
        .strip("`")
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    # ------------------------------------------------------------------
    # 3) Parse JSON
    # ------------------------------------------------------------------
    try:
        data = json.loads(cleaned)
    except Exception as exc:
        logger.error("llm: failed to parse JSON: %s", exc)
        logger.debug("llm raw content: %r", content)
        return {}

    # ------------------------------------------------------------------
    # 4) Build standardized result
    # ------------------------------------------------------------------
    out: Dict[str, Dict[str, Any]] = {}

    for code in kpi_schema.keys():
        entry = data.get(code, {})

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

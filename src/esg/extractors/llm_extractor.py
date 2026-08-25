# src/esg/extractors/llm_extractor.py
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Mapping

from openai import OpenAI

from esg.core.schema import get_canonical_unit, get_synonyms

logger = logging.getLogger(__name__)

# ======================================================================
# System prompt
# ======================================================================

def _build_system_prompt(
    kpi_schema: Mapping[str, Any],
) -> str:
    """
    Build the LLM extraction contract from the supplied KPI schema.

    The prompt must describe only the metrics supplied by the caller so the
    same extractor can support both full-schema benchmark runs and the
    pipeline's missing-KPI fallback mode.
    """
    metric_lines: list[str] = []

    for code, meta in kpi_schema.items():
        value_type = str(
            meta.get("value_type", "quantitative")
        )
        canonical_unit = get_canonical_unit(meta)
        synonyms = get_synonyms(code, meta)

        unit_description = (
            canonical_unit
            if canonical_unit is not None
            else "none"
        )

        metric_lines.append(
            "\n".join(
                [
                    f"- {code}",
                    f"  type: {value_type}",
                    f"  canonical unit: {unit_description}",
                    f"  phrases: {'; '.join(synonyms)}",
                ]
            )
        )

    metrics_text = "\n".join(metric_lines)

    return f"""You are an ESG data extraction model.
Extract ONLY the following metrics if present in the supplied text:

{metrics_text}

Return a JSON object using exactly the supplied metric codes as keys.

For each metric return:
{{
  "raw_value": str | null,
  "raw_unit": str | null
}}

Rules:
- Keep raw_value as close as possible to the reported text.
- Keep raw_unit exactly as reported when a unit is present.
- For qualitative metrics, return the reported qualitative text in raw_value
  and set raw_unit to null.
- Do not infer missing values.
- If a metric is not found, return:
  {{ "raw_value": null, "raw_unit": null }}.
- Do not return metrics that were not listed above.
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
    system_prompt = _build_system_prompt(kpi_schema)

    client = OpenAI(api_key=api_key)
    logger.info("llm: querying model %s", model)

    # ------------------------------------------------------------------
    # 1) Query model
    # ------------------------------------------------------------------
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
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

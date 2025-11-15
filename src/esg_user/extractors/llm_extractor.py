from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from esg_system.config import load_config
from esg_user.prompts.llm_prompts import build_llm_prompt
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)

# Load env vars (OPENAI_API_KEY, OPENAI_MODEL)
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Hard cap on text length to control cost and avoid context issues
MAX_TEXT_CHARS = 40_000

# Retry attempts for malformed JSON
MAX_LLM_RETRIES = 2


# -------------------------------------------------------------------
# LLM backend call
# -------------------------------------------------------------------


def call_llm(prompt: str) -> str:
    """
    Simple wrapper around OpenAI chat.completions API.
    Expects the model to respond with JSON text.
    """
    logger.debug(
        "Calling OpenAI model=%s with prompt length=%d characters",
        DEFAULT_MODEL,
        len(prompt),
    )

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4000,
    )

    content = response.choices[0].message.content or ""
    content = content.strip()

    logger.debug("LLM raw response length: %d characters", len(content))

    return content


# -------------------------------------------------------------------
# JSON parsing helpers
# -------------------------------------------------------------------


def _strip_markdown_fences(s: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` Markdown fences if present.
    """
    s = s.strip()

    # If it starts with triple backticks, remove first fence
    if s.startswith("```"):
        # Remove leading ```
        s = s[3:]
        s = s.lstrip()

        # Drop optional "json" or "JSON"
        if s.lower().startswith("json"):
            s = s[4:]
            s = s.lstrip()

        # Remove trailing fence if present
        fence_pos = s.rfind("```")
        if fence_pos != -1:
            s = s[:fence_pos]

    return s.strip()


def _try_parse_json(s: str) -> Optional[Dict[str, Any]]:
    """
    Try to parse a string as JSON after stripping markdown fences.
    Returns None if parsing fails.
    """
    if not s:
        return None

    cleaned = _strip_markdown_fences(s)

    try:
        obj = json.loads(cleaned)
    except Exception as e:
        logger.warning("LLM JSON parse failed: %s", e)
        return None

    if not isinstance(obj, dict):
        logger.warning("LLM JSON root is not an object (got %s)", type(obj))
        return None

    return obj


# -------------------------------------------------------------------
# Normalization helper
# -------------------------------------------------------------------


def _normalize_llm_dict(
    parsed: Dict[str, Any],
    kpi_codes: List[str],
) -> Dict[str, ExtractorResult]:
    """
    Normalize the parsed LLM JSON into Dict[str, ExtractorResult].

    Expected shape (per KPI code):
      {
        "value": ...,
        "unit": "...",
        "confidence": optional[float]
      }

    We ignore any unknown keys and fill missing ones with safe defaults.
    """
    final: Dict[str, ExtractorResult] = {}

    for code in kpi_codes:
        raw_entry = parsed.get(code, {}) or {}

        value = raw_entry.get("value")
        unit = raw_entry.get("unit")
        confidence = raw_entry.get("confidence")

        # Base confidence: 0.8 if value present, else 0.0
        if isinstance(confidence, (int, float)):
            base_conf = float(confidence)
        else:
            base_conf = 0.8 if value is not None else 0.0

        final[code] = ExtractorResult(
            value=value,
            unit=unit,
            confidence=base_conf,
        )

    return final


# -------------------------------------------------------------------
# Main extractor
# -------------------------------------------------------------------


def extract_kpis_llm(text: str) -> Dict[str, ExtractorResult]:
    """
    LLM-based KPI extractor.

    Steps:
    1. Load KPI schema from config (universal_kpis).
    2. Truncate input text if very long.
    3. Build a prompt instructing the LLM to output strict JSON.
    4. Call the LLM with retry for malformed JSON.
    5. Normalize the response into Dict[str, ExtractorResult].

    If the LLM fails or returns invalid JSON after retries,
    all KPIs get value=None, unit=None, confidence=0.0.
    """
    cfg = load_config()
    kpi_schema = cfg.universal_kpis

    if not kpi_schema:
        logger.warning("LLM extractor: universal_kpis schema is empty.")
        return {}

    kpi_codes: List[str] = list(kpi_schema.keys())

    # Truncate text to avoid excessive cost and context overflow
    if len(text) > MAX_TEXT_CHARS:
        logger.info(
            "LLM extractor: truncating text from %d to %d characters.",
            len(text),
            MAX_TEXT_CHARS,
        )
        text = text[:MAX_TEXT_CHARS]

    prompt = build_llm_prompt(text, kpi_schema)

    parsed: Optional[Dict[str, Any]] = None

    # Retry loop for JSON parsing
    for attempt in range(MAX_LLM_RETRIES + 1):
        try:
            raw_response = call_llm(prompt)
        except Exception as e:
            logger.error("LLM call failed on attempt %d: %s", attempt + 1, e)
            break

        parsed = _try_parse_json(raw_response)

        if parsed is not None:
            logger.info("LLM extractor: successfully parsed JSON on attempt %d", attempt + 1)
            break

        logger.warning("LLM extractor: invalid JSON on attempt %d", attempt + 1)

    if parsed is None:
        # Total failure → return null KPIs
        logger.error("LLM extractor: giving up after %d attempts; returning empty results.", MAX_LLM_RETRIES + 1)
        return {
            code: ExtractorResult(value=None, unit=None, confidence=0.0)
            for code in kpi_codes
        }

    # Normalize the parsed dict into ExtractorResult objects
    final = _normalize_llm_dict(parsed, kpi_codes)

    logger.debug("LLM extractor final parsed KPIs: %s", final)

    return final

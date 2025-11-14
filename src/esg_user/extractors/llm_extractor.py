import json
from typing import Dict, Any
from esg_system.config import load_config
from esg_user.prompts.llm_prompts import build_llm_prompt


# -----------------------------
# Backend Placeholder
# -----------------------------

def call_llm(prompt: str) -> str:
    """
    Call the LLM backend with the given prompt and return the raw string response.

    This is a placeholder. You must implement this for a real model.

    Example for OpenAI (pseudo-code):

        from openai import OpenAI

        client = OpenAI()

        def call_llm(prompt: str) -> str:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content

    Until you implement this, the extractor will fall back to returning
    empty results (all values None) so the pipeline still runs.
    """
    raise NotImplementedError("LLM backend not configured. Implement call_llm() to enable LLM extraction.")


# -----------------------------
# Parsing Helper
# -----------------------------

def _safe_json_loads(s: str) -> Dict[str, Any]:
    """
    Safely parse JSON, returning an empty dict on failure.
    """
    try:
        return json.loads(s)
    except Exception:
        return {}


# -----------------------------
# Main Extraction Function
# -----------------------------

def extract_kpis_llm(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Schema-guided ESG KPI extraction using an LLM.

    Steps:
    - Load KPI schema (universal_kpis)
    - Build a controlled prompt
    - Send it to the LLM backend (via call_llm)
    - Parse JSON output
    - Normalize result to include all KPI codes
    """

    cfg = load_config()
    kpi_schema = cfg.universal_kpis  # dict of KPI codes -> metadata

    # If schema is empty, just return an empty dict
    if not kpi_schema:
        return {}

    prompt = build_llm_prompt(text, kpi_schema)

    try:
        llm_response = call_llm(prompt)
    except NotImplementedError:
        # Fallback: return empty results, but with all keys present
        return {
            code: {"value": None, "unit": None}
            for code in kpi_schema.keys()
        }

    parsed = _safe_json_loads(llm_response)

    # Normalize: ensure every KPI code is present with value/unit keys
    final: Dict[str, Dict[str, Any]] = {}

    for kpi_code in kpi_schema.keys():
        item = parsed.get(kpi_code, {})
        final[kpi_code] = {
            "value": item.get("value"),
            "unit": item.get("unit"),
        }

    return final
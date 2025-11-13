import json
from typing import Dict, Any
from esg_system.config import load_config
from esg_user.prompts.llm_prompts import build_llm_prompt


# -----------------------------
# Backend Placeholder
# -----------------------------

def call_llm(prompt: str) -> str:
    """
    Placeholder LLM call.
    Replace this function with your preferred LLM client 
    (OpenAI, Anthropic, Groq, LM Studio, Ollama, etc.)

    For now, it raises a clear message so we don't accidentally call an API.
    """
    raise NotImplementedError(
        "LLM backend not configured. Please implement call_llm() to use a real model."
    )


# -----------------------------
# Parsing Helper
# -----------------------------

def safe_json_loads(s: str) -> Dict[str, Any]:
    """
    Safely parse JSON. If parsing fails, return empty dict.
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
    - Load KPI schema
    - Construct a controlled prompt
    - Send to LLM backend
    - Parse JSON output
    """

    cfg = load_config()

    # For now: only universal KPIs
    kpi_schema = cfg.universal_kpis

    prompt = build_llm_prompt(text, kpi_schema)

    try:
        llm_response = call_llm(prompt)
    except NotImplementedError:
        # For development: return empty, but with the right structure
        return {k: {"value": None, "unit": None} for k in kpi_schema.keys()}

    extracted = safe_json_loads(llm_response)

    # Normalize result: ensure all keys present
    final = {}

    for kpi_code in kpi_schema.keys():
        item = extracted.get(kpi_code, {})
        final[kpi_code] = {
            "value": item.get("value"),
            "unit": item.get("unit"),
        }

    return final

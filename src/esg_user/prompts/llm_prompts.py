from typing import Dict, Any


def build_llm_prompt(text: str, kpi_schema: Dict[str, Any]) -> str:
    """
    Build a schema-guided prompt asking the LLM to extract KPI values.

    The model receives:
    - A list of KPI codes (and optional names/units if present in the schema)
    - The full ESG text to analyze
    - Strict JSON-only output instructions
    """

    # Prepare a readable description of the KPIs
    kpi_descriptions = []
    for code, info in kpi_schema.items():
        name = info.get("name", code)
        unit = info.get("unit")
        if unit:
            kpi_descriptions.append(f"- {code}: {name} (unit: {unit})")
        else:
            kpi_descriptions.append(f"- {code}: {name}")

    kpi_block = "\n".join(kpi_descriptions)

    prompt = f"""
You are an assistant specialized in ESG (Environmental, Social, Governance) report analysis.

Your task:
Extract ONLY the KPI values for the KPI codes listed below from the given text.

KPI schema:
{kpi_block}

Text to analyze:
\"\"\"{text}\"\"\"

Rules:
- Consider all relevant parts of the text.
- For each KPI code, either:
    - extract a numeric value and its unit (if available), or
    - return null if the KPI is not mentioned or cannot be reliably determined.
- Do NOT invent or guess values.
- If multiple values appear for the same KPI, choose the most recent or most clearly reported one.
- If the unit is not explicitly given but can be inferred reliably from the context, you may fill it in.
- If the unit is unclear, set the unit to null.

Output format (JSON only, no extra text):
{{
  "total_ghg_emissions": {{"value": 123400, "unit": "tCO2e"}},
  "energy_consumption": {{"value": 500000, "unit": "MWh"}},
  "water_withdrawal": {{"value": null, "unit": "m3"}}
}}

Now produce the JSON object with the same structure, but using the KPI codes from the schema above.
If a KPI is not found, return {{"value": null, "unit": null}} for that KPI.
"""

    return prompt.strip()

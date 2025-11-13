def build_llm_prompt(text: str, kpi_schema: dict) -> str:
    """
    Build a schema-guided prompt asking the LLM to extract KPI values.

    The model sees:
    - The list of KPIs (their canonical names)
    - A clear instruction to extract values from the given text
    - A strict JSON output requirement
    """
    kpi_list = list(kpi_schema.keys())

    prompt = f"""
You are an assistant specialized in ESG report analysis.

Extract ONLY the following KPIs from the text:
{kpi_list}

Text to analyze:
\"\"\"{text}\"\"\"

Rules:
- Return JSON only
- Use KPI codes as keys
- Use null when KPI is not found
- Extract value and unit when present
- Do not guess values

Output format:
{{
  "kpi_code": {{ "value": number|null, "unit": string|null }}
}}
    """

    return prompt.strip()

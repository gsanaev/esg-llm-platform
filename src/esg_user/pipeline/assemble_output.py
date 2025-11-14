import json
from typing import Dict, Any, Optional
from datetime import datetime


def assemble_output(
    normalized_kpis: Dict[str, Dict[str, Any]],
    source_pdf: Optional[str] = None,
    extraction_method_version: str = "v1"
) -> Dict[str, Any]:
    """
    Build the final structured output for a single ESG document.
    """

    output = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "schema_version": "universal_v1",
            "extraction_method_version": extraction_method_version,
            "source_pdf": source_pdf,
        },
        "kpi_results": normalized_kpis,
    }

    return output


def export_to_json(data: Dict[str, Any], path: str) -> None:
    """
    Save assembled output to a JSON file.
    """

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

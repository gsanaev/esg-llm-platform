from __future__ import annotations

import logging
from typing import Dict, Any

from esg_system.config import load_config
from esg_user.types import ExtractorResult

logger = logging.getLogger(__name__)


def assemble_output(
    normalized_kpis: Dict[str, ExtractorResult]
) -> Dict[str, Dict[str, Any]]:
    """
    Build the final enriched KPI output using the universal KPI schema.

    Output shape (Option B):
    {
        "kpi_code": {
            "label": str,
            "description": str | None,
            "value": float | None,
            "unit": str | None,
            "confidence": float,
        },
        ...
    }
    """

    cfg = load_config()
    schema = cfg.universal_kpis

    final: Dict[str, Dict[str, Any]] = {}

    for code, entry in normalized_kpis.items():
        if not isinstance(entry, dict):
            logger.warning(
                "assemble_output: invalid KPI entry for %s (type=%s). Skipping.",
                code,
                type(entry),
            )
            continue

        meta = schema.get(code, {})

        label = meta.get("label", code.replace("_", " ").title())
        description = meta.get("description", None)

        final[code] = {
            "label": label,
            "description": description,
            "value": entry.get("value"),
            "unit": entry.get("unit"),
            "confidence": entry.get("confidence", 0.0),
        }

    return final

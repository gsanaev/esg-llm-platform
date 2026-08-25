from __future__ import annotations

from typing import Any, Mapping

from esg.extractors.table_grid_extractor import extract_kpis_tables_grid
from esg.normalization.table_grid_normalizer import (
    normalize_table_grid_result,
)


def run_benchmark_method(
    pdf_path: str,
    *,
    method: str,
    kpi_schema: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Run one extraction method independently for benchmark evaluation.

    This runner deliberately performs no fusion, reconciliation,
    ground-truth access, or benchmark scoring.
    """
    if method != "table_grid":
        raise ValueError(
            f"Unsupported benchmark extraction method: {method}"
        )

    raw = extract_kpis_tables_grid(
        pdf_path,
        kpi_schema,
    )

    return normalize_table_grid_result(
        raw,
        kpi_schema,
    )

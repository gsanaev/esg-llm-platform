from __future__ import annotations

from typing import Any, Mapping

from esg.extractors.table_grid_extractor import extract_kpis_tables_grid
from esg.normalization.table_grid_normalizer import (
    normalize_table_grid_result,
)

from esg.extractors.table_plain_extractor import extract_kpis_tables_plain
from esg.normalization.table_plain_normalizer import (
    normalize_table_plain_result,
)

from esg.extractors.regex_extractor import extract_kpis_regex
from esg.normalization.regex_normalizer import normalize_regex_result
from esg.utils.pdf_reader import extract_text

from esg.extractors.nlp_extractor import extract_kpis_nlp
from esg.normalization.nlp_normalizer import normalize_nlp_result

from esg.extractors.llm_extractor import extract_kpis_llm
from esg.normalization.llm_normalizer import normalize_llm_result


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
    if method == "table_grid":
        raw = extract_kpis_tables_grid(
            pdf_path,
            kpi_schema,
        )

        return normalize_table_grid_result(
            raw,
            kpi_schema,
        )

    if method == "table_plain":
        raw = extract_kpis_tables_plain(
            pdf_path,
            kpi_schema,
        )

        return normalize_table_plain_result(
            raw,
            kpi_schema,
        )
    if method == "regex":
        text = extract_text(pdf_path)

        raw = extract_kpis_regex(
            text,
            kpi_schema,
        )

        return normalize_regex_result(
            raw,
            kpi_schema,
        )
    if method == "nlp":
        text = extract_text(pdf_path)

        raw = extract_kpis_nlp(
            text,
            kpi_schema,
        )

        return normalize_nlp_result(
            raw,
            kpi_schema,
        )
    if method == "llm":
        text = extract_text(pdf_path)

        raw = extract_kpis_llm(
            text,
            kpi_schema,
        )

        return normalize_llm_result(
            raw,
            kpi_schema,
        )

    raise ValueError(
        f"Unsupported benchmark extraction method: {method}"
    )

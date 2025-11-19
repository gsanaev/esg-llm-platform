from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Mapping

from esg.utils.pdf_reader import extract_text
from esg.config import load_config

# Extractors
from esg.extractors.regex_extractor import extract_kpis_regex
from esg.extractors.table_grid_extractor import extract_kpis_tables_grid
from esg.extractors.table_plain_extractor import extract_kpis_tables_plain
from esg.extractors.nlp_extractor import extract_kpis_nlp
from esg.extractors.llm_extractor import extract_kpis_llm

# Normalizers
from esg.normalization.regex_normalizer import normalize_regex_result
from esg.normalization.table_grid_normalizer import normalize_table_grid_result
from esg.normalization.table_plain_normalizer import normalize_table_plain_result
from esg.normalization.nlp_normalizer import normalize_nlp_result
from esg.normalization.llm_normalizer import normalize_llm_result

# Output structure
from esg.core.types import KPIResult

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Fusion priority (deterministic only):
#   table_grid → table_plain → regex → nlp
#
# LLM is handled *separately* as a final backfill step,
# and never overwrites an existing value.
# ----------------------------------------------------------
def fuse_all_sources(
    regex_norm: Mapping[str, Any],
    table_grid_norm: Mapping[str, Any],
    table_plain_norm: Mapping[str, Any],
    nlp_norm: Mapping[str, Any],
    llm_norm: Mapping[str, Any],
    kpi_codes: List[str],
) -> Dict[str, Dict[str, Any]]:

    fused: Dict[str, Dict[str, Any]] = {}

    for code in kpi_codes:
        best = None

        v3 = table_grid_norm.get(code)
        v2 = table_plain_norm.get(code)
        rx = regex_norm.get(code)
        ll = llm_norm.get(code)
        nl = nlp_norm.get(code)

        # Priority 1: table
        if v3:
            best = {**v3, "source": ["table_grid"]}

        # Priority 2: table
        elif v2:
            best = {**v2, "source": ["table_plain"]}

        # Priority 3: regex
        elif rx:
            best = {**rx, "source": ["regex"]}

        # Priority 4: LLM
        elif ll:
            best = {**ll, "source": ["llm"]}

        # Priority 5: NLP
        elif nl:
            best = {**nl, "source": ["nlp"]}

        # Priority 6: no data anywhere
        else:
            best = {
                "value": None,
                "unit": None,
                "confidence": 0.0,
                "source": [],
            }

        fused[code] = best

    return fused


# ----------------------------------------------------------
# Main Pipeline
# ----------------------------------------------------------
class ESGPipelineV2:
    """
    Unified v2 pipeline combining:
        - table_grid (grid tables)
        - table_plain (text-based tables)
        - regex (raw text)
        - nlp   (sentence-level extraction)
        - llm   (final backfill for missing KPIs)
    """

    def run_on_pdf(self, pdf_path: str) -> List[KPIResult]:
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(pdf_path)

        # Load KPI schema
        cfg = load_config()
        kpi_schema = cfg.universal_kpis
        kpi_codes: List[str] = list(kpi_schema.keys())

        # Extract plain text from PDF
        text = extract_text(str(path))

        # --------------------------------------------------
        # 1) Deterministic extractors (no LLM here)
        # --------------------------------------------------
        table_grid_raw = extract_kpis_tables_grid(str(path), kpi_schema)
        table_plain_raw = extract_kpis_tables_plain(str(path), kpi_schema)
        regex_raw = extract_kpis_regex(text, kpi_schema)
        nlp_raw = extract_kpis_nlp(text, kpi_schema)

        # Normalize deterministic outputs
        table_grid_norm = normalize_table_grid_result(table_grid_raw, kpi_schema)
        table_plain_norm = normalize_table_plain_result(table_plain_raw, kpi_schema)
        regex_norm = normalize_regex_result(regex_raw, kpi_schema)
        nlp_norm = normalize_nlp_result(nlp_raw, kpi_schema)

        # Fuse deterministic sources
        fused = fuse_all_sources(
            regex_norm=regex_norm,
            table_grid_norm=table_grid_norm,
            table_plain_norm=table_plain_norm,
            nlp_norm=nlp_norm,
            llm_norm={},           
            kpi_codes=kpi_codes,
        )   

        # --------------------------------------------------
        # 2) LLM backfill (Option B – Hybrid Assist)
        #    Only for KPIs where value is still None.
        # --------------------------------------------------
        missing_codes = [
            code for code in kpi_codes
            if fused.get(code, {}).get("value") is None
        ]

        if missing_codes:
            logger.info(
                "pipeline: %d KPIs missing after deterministic extractors; "
                "using llm backfill.",
                len(missing_codes),
            )

            # Restrict schema passed to LLM to missing KPIs only
            subset_schema: Dict[str, Any] = {
                code: kpi_schema[code]
                for code in missing_codes
                if code in kpi_schema
            }

            try:
                llm_raw = extract_kpis_llm(text, subset_schema)
                llm_norm = normalize_llm_result(llm_raw, subset_schema)
            except Exception as exc:
                logger.warning("pipeline: llm backfill failed: %s", exc)
                llm_norm = {}

            # Fill only those KPIs that are still missing
            for code in missing_codes:
                entry = llm_norm.get(code)
                if not entry:
                    continue

                # Do NOT overwrite any non-missing values (extra safety guard)
                if fused.get(code, {}).get("value") is not None:
                    continue

                fused[code] = {
                    **entry,
                    "source": ["llm"],
                }

        # --------------------------------------------------
        # 3) Convert to KPIResult objects
        # --------------------------------------------------
        results: List[KPIResult] = []
        for code, entry in fused.items():
            results.append(
                KPIResult(
                    code=code,
                    value=entry.get("value"),
                    unit=entry.get("unit"),
                    confidence=float(entry.get("confidence", 0.0)),
                    source=entry.get("source") or [],
                )
            )

        return results


# Convenience API
def run_pipeline(pdf_path: str) -> List[KPIResult]:
    return ESGPipelineV2().run_on_pdf(pdf_path)

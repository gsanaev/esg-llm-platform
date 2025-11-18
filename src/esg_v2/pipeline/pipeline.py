from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Mapping

from esg_system.core.pdf_reader import extract_text
from esg_system.config import load_config

# Extractors
from esg_v2.extractors.regex_extractor_v2 import extract_kpis_regex_v2
from esg_v2.extractors.table_extractor_v2 import extract_kpis_from_tables_v2
from esg_v2.extractors.table_extractor_v3 import extract_kpis_from_tables_v3
from esg_v2.extractors.nlp_extractor_v2 import extract_kpis_nlp_v2
from esg_v2.extractors.llm_extractor_v2 import extract_kpis_llm_v2

# Normalizers
from esg_v2.normalization.regex_normalizer import normalize_regex_result_v2
from esg_v2.normalization.table_normalizer_v2 import normalize_table_result_v2
from esg_v2.normalization.table_normalizer_v3 import normalize_table_result_v3
from esg_v2.normalization.nlp_normalizer_v2 import normalize_nlp_result_v2
from esg_v2.normalization.llm_normalizer_v2 import normalize_llm_result_v2

# Output structure
from esg_v2.core.types import KPIResult

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Fusion priority (deterministic only):
#   table_v3 → table_v2 → regex_v2 → nlp_v2
#
# LLM is handled *separately* as a final backfill step,
# and never overwrites an existing value.
# ----------------------------------------------------------
def fuse_all_sources(
    regex_norm: Mapping[str, Any],
    table_v2_norm: Mapping[str, Any],
    table_v3_norm: Mapping[str, Any],
    nlp_norm: Mapping[str, Any],
    llm_norm: Mapping[str, Any],
    kpi_codes: List[str],
) -> Dict[str, Dict[str, Any]]:

    fused: Dict[str, Dict[str, Any]] = {}

    for code in kpi_codes:
        best = None

        v3 = table_v3_norm.get(code)
        v2 = table_v2_norm.get(code)
        rx = regex_norm.get(code)
        ll = llm_norm.get(code)
        nl = nlp_norm.get(code)

        # Priority 1: table_v3
        if v3:
            best = {**v3, "source": ["table_v3"]}

        # Priority 2: table_v2
        elif v2:
            best = {**v2, "source": ["table_v2"]}

        # Priority 3: regex
        elif rx:
            best = {**rx, "source": ["regex_v2"]}

        # Priority 4: LLM
        elif ll:
            best = {**ll, "source": ["llm_v2"]}

        # Priority 5: NLP
        elif nl:
            best = {**nl, "source": ["nlp_v2"]}

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
        - table_v3 (grid tables)
        - table_v2 (text-based tables)
        - regex_v2 (raw text)
        - nlp_v2   (sentence-level extraction)
        - llm_v2   (final backfill for missing KPIs)
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
        table_v3_raw = extract_kpis_from_tables_v3(str(path), kpi_schema)
        table_v2_raw = extract_kpis_from_tables_v2(str(path), kpi_schema)
        regex_raw = extract_kpis_regex_v2(text, kpi_schema)
        nlp_raw = extract_kpis_nlp_v2(text, kpi_schema)

        # Normalize deterministic outputs
        table_v3_norm = normalize_table_result_v3(table_v3_raw, kpi_schema)
        table_v2_norm = normalize_table_result_v2(table_v2_raw, kpi_schema)
        regex_norm = normalize_regex_result_v2(regex_raw, kpi_schema)
        nlp_norm = normalize_nlp_result_v2(nlp_raw, kpi_schema)

        # Fuse deterministic sources
        fused = fuse_all_sources(
            regex_norm=regex_norm,
            table_v2_norm=table_v2_norm,
            table_v3_norm=table_v3_norm,
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
                "pipeline_v2: %d KPIs missing after deterministic extractors; "
                "using llm_v2 backfill.",
                len(missing_codes),
            )

            # Restrict schema passed to LLM to missing KPIs only
            subset_schema: Dict[str, Any] = {
                code: kpi_schema[code]
                for code in missing_codes
                if code in kpi_schema
            }

            try:
                llm_raw = extract_kpis_llm_v2(text, subset_schema)
                llm_norm = normalize_llm_result_v2(llm_raw, subset_schema)
            except Exception as exc:
                logger.warning("pipeline_v2: llm_v2 backfill failed: %s", exc)
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
                    "source": ["llm_v2"],
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
def run_pipeline_v2(pdf_path: str) -> List[KPIResult]:
    return ESGPipelineV2().run_on_pdf(pdf_path)

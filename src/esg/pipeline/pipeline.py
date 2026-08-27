# src/esg/pipeline/pipeline.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, List, Mapping

from esg.utils.pdf_reader import extract_text
from esg.config import load_config

# Extractors
from esg.extractors.regex_extractor import (
    extract_kpi_candidates_regex,
    extract_kpis_regex,
)
from esg.extractors.table_grid_extractor import (
    extract_kpi_candidates_tables_grid,
    extract_kpis_tables_grid,
)
from esg.extractors.table_plain_extractor import (
    extract_kpi_candidates_tables_plain,
    extract_kpis_tables_plain,
)
from esg.extractors.nlp_extractor import (
    extract_kpi_candidates_nlp,
    extract_kpis_nlp,
)
from esg.extractors.llm_extractor import extract_kpis_llm

# Normalizers
from esg.normalization.regex_normalizer import normalize_regex_result
from esg.normalization.table_grid_normalizer import normalize_table_grid_result
from esg.normalization.table_plain_normalizer import normalize_table_plain_result
from esg.normalization.nlp_normalizer import normalize_nlp_result
from esg.normalization.llm_normalizer import normalize_llm_result

# Output structure
from esg.core.types import (
    EvidenceCandidate,
    KPIResult,
    ReconciledKPIResult,
)
from esg.pipeline.evidence import (
    normalized_results_to_evidence,
    raw_candidate_results_to_evidence,
)

from esg.pipeline.reconciliation import reconcile_metric_evidence

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Score-based deterministic fusion
#
# Rules:
#   1. Deterministic extractors compete by score
#   2. Hard priority used only as tie-breaker:
#        table_grid > table_plain > regex > nlp
#   3. LLM handled separately & never overwrites filled values
# ----------------------------------------------------------

def fuse_all_sources(
    regex_norm: Mapping[str, Any],
    table_grid_norm: Mapping[str, Any],
    table_plain_norm: Mapping[str, Any],
    nlp_norm: Mapping[str, Any],
    kpi_codes: List[str],
) -> Dict[str, Dict[str, Any]]:

    fused: Dict[str, Dict[str, Any]] = {}

    # Deterministic priority (tie-break only)
    PRIORITY_ORDER = {
        "table_grid": 4,
        "table_plain": 3,
        "regex": 2,
        "nlp": 1,
    }

    for code in kpi_codes:
        candidates = []

        # Collect candidates if present
        for src_name, src_dict in [
            ("table_grid", table_grid_norm),
            ("table_plain", table_plain_norm),
            ("regex", regex_norm),
            ("nlp", nlp_norm),
        ]:
            entry = src_dict.get(code)
            if entry:
                score = entry.get("_score", {}).get("score", 0.0)
                candidates.append({
                    "source": src_name,
                    "entry": entry,
                    "score": score,
                    "priority": PRIORITY_ORDER[src_name],
                })

        # If nothing extracted at all → leave empty
        if not candidates:
            fused[code] = {
                "value": None,
                "unit": None,
                "confidence": 0.0,
                "source": [],
                "status": "Not Reported",
            }
            continue


        # Sort by score first, then deterministic priority
        best = sorted(
            candidates,
            key=lambda c: (c["score"], c["priority"]),
            reverse=True
        )[0]

        fused[code] = {
            **best["entry"],
            "source": [best["source"]],
        }

    return fused


# ----------------------------------------------------------
# Main Pipeline
# ----------------------------------------------------------
class ESGPipeline:
    """
    Unified ESG KPI extraction and reconciliation pipeline combining:
        - table_grid (grid tables)
        - table_plain (text-based tables)
        - regex (raw text)
        - nlp   (sentence-level extraction)
        - llm   (final backfill for missing KPIs)
    """

    def run_on_pdf_with_evidence(
        self,
        pdf_path: str,
    ) -> tuple[List[KPIResult], List[EvidenceCandidate]]:
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

        # Preserve all deterministic observations for later reconciliation
        table_grid_candidates = extract_kpi_candidates_tables_grid(
            str(path),
            kpi_schema,
        )
        table_plain_candidates = extract_kpi_candidates_tables_plain(
            str(path),
            kpi_schema,
        )
        regex_candidates = extract_kpi_candidates_regex(
            text,
            kpi_schema,
        )
        nlp_candidates = extract_kpi_candidates_nlp(
            text,
            kpi_schema,
        )

        evidence: List[EvidenceCandidate] = []

        for method, raw_candidates, normalizer in [
            (
                "table_grid",
                table_grid_candidates,
                normalize_table_grid_result,
            ),
            (
                "table_plain",
                table_plain_candidates,
                normalize_table_plain_result,
            ),
            (
                "regex",
                regex_candidates,
                normalize_regex_result,
            ),
            (
                "nlp",
                nlp_candidates,
                normalize_nlp_result,
            ),
        ]:
            evidence.extend(
                raw_candidate_results_to_evidence(
                    raw_candidates,
                    kpi_schema=kpi_schema,
                    normalizer=normalizer,
                    source_document=str(path),
                    extraction_method=method,
                )
            )

        # Fuse deterministic sources
        fused = fuse_all_sources(
            regex_norm=regex_norm,
            table_grid_norm=table_grid_norm,
            table_plain_norm=table_plain_norm,
            nlp_norm=nlp_norm,
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

            evidence.extend(
                normalized_results_to_evidence(
                    llm_norm,
                    source_document=str(path),
                    extraction_method="llm",
                )
            )

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
                    status=entry.get("status", "Not Reported"),
                )
            )

        return results, evidence

    def run_on_pdf_reconciled(
        self,
        pdf_path: str,
    ) -> List[ReconciledKPIResult]:
        """
        Run the pipeline and reconcile preserved evidence into final results.

        The compact run_on_pdf() API remains available for simpler extraction use cases.
        """
        _, evidence = self.run_on_pdf_with_evidence(pdf_path)

        cfg = load_config()
        kpi_codes = list(cfg.universal_kpis.keys())

        return [
            reconcile_metric_evidence(
                code,
                evidence,
            )
            for code in kpi_codes
        ]

    def run_on_pdf(self, pdf_path: str) -> List[KPIResult]:
        """
        Return compact KPI results from the extraction/fusion path.
        """
        results, _ = self.run_on_pdf_with_evidence(pdf_path)
        return results


# Backward-compatible alias for the 2.0 public class name.
ESGPipelineV2 = ESGPipeline


# Convenience API
def run_pipeline(pdf_path: str) -> List[KPIResult]:
    return ESGPipeline().run_on_pdf(pdf_path)

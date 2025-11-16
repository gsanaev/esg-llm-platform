# src/esg_v2/pipeline/pipeline.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any, Mapping

from esg_system.core.pdf_reader import extract_text
from esg_system.config import load_config

from esg_user.pipeline.extract_kpis import extract_all_kpis

from esg_v2.core.types import KPIResult
from esg_v2.extractors.regex_extractor_v2 import extract_kpis_regex_v2
from esg_v2.normalization.regex_normalizer import normalize_regex_result_v2

logger = logging.getLogger(__name__)


class ESGPipelineV2:
    """
    High-level v2 ESG pipeline façade.

    Responsibilities:
    - Receive a PDF path
    - Extract cleaned text (delegates to esg_system)
    - Run v2 regex extractor (number + unit aware)
    - Run v1 full pipeline as fallback
    - Fuse v2 regex with v1 (v2 fixes v1 where needed)
    - Convert fused dict into KPIResult objects
    """

    def __init__(self) -> None:
        # Later we could inject config, feature flags, etc.
        pass

    def run_on_pdf(self, pdf_path: str) -> List[KPIResult]:
        """
        Execute the full ESG KPI pipeline (v2).

        Parameters
        ----------
        pdf_path : str
            Path to the ESG report PDF.

        Returns
        -------
        List[KPIResult]
            List of normalized KPI results in v2 format.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # 1) Extract text
        logger.info("v2: Extracting text from '%s'…", pdf_path)
        text = extract_text(str(path))

        # 2) Load KPI schema (for list of KPI codes)
        cfg = load_config()
        kpi_schema = cfg.universal_kpis
        kpi_codes: List[str] = list(kpi_schema.keys())

        # 3) v2 regex extractor (unit-aware + numeric-safe)
        logger.info("v2: Running regex extractor (v2)…")
        regex_raw = extract_kpis_regex_v2(text, kpi_schema)
        regex_norm = normalize_regex_result_v2(regex_raw)
        logger.debug("v2: Normalized regex result: %s", regex_norm)

        # 4) v1 pipeline (regex + NLP + tables + LLM + fusion)
        logger.info("v2: Running fallback v1 extraction pipeline…")
        v1_results: Mapping[str, Mapping[str, Any]] = extract_all_kpis(text, str(path))
        logger.debug("v2: Raw v1 fused result: %s", v1_results)

        # 5) Fuse v2 regex on top of v1
        fused: Dict[str, Dict[str, Any]] = self._fuse_regex_v1(
            regex_norm=regex_norm,
            v1_results=v1_results,
            kpi_codes=kpi_codes,
        )
        logger.debug("v2: Fused KPI dict (regex + v1): %s", fused)

        # 6) Convert to structured KPIResult objects
        return self._convert_to_kpi_results(fused)

    # ------------------------------------------------------------------
    # Fusion logic: v2 regex + v1 fused result
    # ------------------------------------------------------------------

    def _fuse_regex_v1(
        self,
        regex_norm: Mapping[str, Mapping[str, Any]],
        v1_results: Mapping[str, Mapping[str, Any]],
        kpi_codes: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Combine v2 regex output with the v1 fused result.

        Rules per KPI:
        - Start from v1 result (it already includes NLP + tables + LLM)
        - If v2 regex has a numeric value:
            * Override value
            * Override unit from raw_unit (or unit) if available
            * Keep source and append 'regex_v2'
            * Confidence = max(v1_confidence, regex_confidence)
        """
        fused: Dict[str, Dict[str, Any]] = {}

        for code in kpi_codes:
            base: Dict[str, Any] = dict(v1_results.get(code, {}))
            override = regex_norm.get(code)

            if override and override.get("value") is not None:
                # --- value ---
                base["value"] = override["value"]

                # --- unit ---
                unit_from_regex = override.get("raw_unit") or override.get("unit")
                if unit_from_regex is not None:
                    base["unit"] = unit_from_regex

                # --- raw_value / raw_unit (for debugging / traceability) ---
                if "raw_value" in override:
                    base["raw_value"] = override["raw_value"]
                if "raw_unit" in override:
                    base["raw_unit"] = override["raw_unit"]

                # --- source tracking ---
                src = base.get("source")
                if isinstance(src, list):
                    if "regex_v2" not in src:
                        src.append("regex_v2")
                elif isinstance(src, str):
                    base["source"] = [src, "regex_v2"]
                else:
                    base["source"] = ["regex_v2"]

                # --- confidence: use best of both worlds ---
                v1_conf_raw = base.get("confidence", 0.0)
                try:
                    v1_conf = float(v1_conf_raw) if v1_conf_raw is not None else 0.0
                except (TypeError, ValueError):
                    v1_conf = 0.0

                regex_conf_raw = override.get("confidence", 0.0)
                try:
                    regex_conf = float(regex_conf_raw) if regex_conf_raw is not None else 0.0
                except (TypeError, ValueError):
                    regex_conf = 0.0

                base["confidence"] = max(v1_conf, regex_conf)

            fused[code] = base

        logger.info("v2: Fused %d KPIs (regex + v1).", len(fused))
        return fused

    # ------------------------------------------------------------------
    # Conversion: dict → KPIResult dataclasses
    # ------------------------------------------------------------------

    def _convert_to_kpi_results(
        self,
        raw_results: Mapping[str, Mapping[str, Any]],
    ) -> List[KPIResult]:
        """
        Convert fused KPI dict into a list of KPIResult objects.
        """
        kpis: List[KPIResult] = []

        for code, entry in raw_results.items():
            value = entry.get("value")
            unit = entry.get("unit")

            conf_raw = entry.get("confidence", 0.0)
            try:
                confidence = float(conf_raw) if conf_raw is not None else 0.0
            except (TypeError, ValueError):
                confidence = 0.0

            raw_source = entry.get("source", [])
            if isinstance(raw_source, list):
                source = [str(s) for s in raw_source]
            elif isinstance(raw_source, str):
                source = [raw_source]
            else:
                source = []

            kpi = KPIResult(
                code=code,
                value=value,
                unit=unit,
                confidence=confidence,
                source=source,
            )
            kpis.append(kpi)

        logger.info("v2: Converted %d KPIs into KPIResult objects.", len(kpis))
        return kpis


# ---------------------------------------------------------------------
# Functional wrapper API (for notebooks + CLI)
# ---------------------------------------------------------------------

def run_pipeline_v2(pdf_path: str) -> List[KPIResult]:
    """
    Thin convenience wrapper used by notebooks and CLI.

    Example
    -------
    from esg_v2.pipeline.pipeline import run_pipeline_v2
    results = run_pipeline_v2("data/raw/report.pdf")
    """
    pipeline = ESGPipelineV2()
    return pipeline.run_on_pdf(pdf_path)

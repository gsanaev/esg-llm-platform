# src/esg/cli/run.py

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from esg.core.types import KPIResult
from esg.pipeline.pipeline import ESGPipelineV2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _kpi_result_to_dict(kpi: KPIResult) -> Dict[str, Any]:
    """
    Serialize KPIResult to a JSON-friendly dict.
    """
    return {
        "code": kpi.code,
        "value": kpi.value,
        "unit": kpi.unit,
        "confidence": kpi.confidence,
        "source": kpi.source,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ESG KPI extraction pipeline (v2 façade)."
    )
    parser.add_argument(
        "input",
        help="Path to input ESG report PDF.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Path to output JSON file (default: output.json).",
        default="output.json",
    )

    args = parser.parse_args()

    pdf_path = args.input
    output_path = args.output

    logger.info("v2 CLI: Starting ESG pipeline on '%s'", pdf_path)

    pipeline = ESGPipelineV2()
    kpis: List[KPIResult] = pipeline.run_on_pdf(pdf_path)

    data = {
        "pdf_path": pdf_path,
        "kpis": [_kpi_result_to_dict(k) for k in kpis],
    }

    out_file = Path(output_path)
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    logger.info("v2 CLI: Saved results to %s", out_file)


if __name__ == "__main__":
    main()

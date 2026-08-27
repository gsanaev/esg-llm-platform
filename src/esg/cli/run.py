# src/esg/cli/run.py

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from esg.core.types import ReconciledKPIResult
from esg.pipeline.pipeline import ESGPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _reconciled_result_to_dict(
    result: ReconciledKPIResult,
) -> dict[str, Any]:
    """Serialize a reconciled KPI result to a JSON-friendly dictionary."""
    return asdict(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evidence-based ESG KPI extraction and reconciliation pipeline."
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

    logger.info(
        "Starting reconciled ESG pipeline on '%s'",
        pdf_path,
    )

    pipeline = ESGPipeline()
    results = pipeline.run_on_pdf_reconciled(pdf_path)

    data = {
        "pdf_path": pdf_path,
        "results": [
            _reconciled_result_to_dict(result)
            for result in results
        ],
    }

    out_file = Path(output_path)
    out_file.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    logger.info("Saved reconciled results to %s", out_file)


if __name__ == "__main__":
    main()

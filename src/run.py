from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from esg_system.core.pdf_reader import extract_text
from esg_user.pipeline.extract_kpis import extract_all_kpis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ESG KPI Extraction CLI")

    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to the PDF ESG report",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Where to save the extracted KPIs as JSON",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    pdf_path = Path(args.input)
    if not pdf_path.exists():
        logger.error("Input PDF not found: %s", pdf_path)
        return

    # Step 1: extract raw text
    logger.info("Extracting text...")
    text = extract_text(str(pdf_path))

    # Step 2: extract KPIs
    logger.info("Running KPI pipeline...")
    results = extract_all_kpis(text=text, pdf_path=str(pdf_path))

    # Optional: save as JSON
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info("Saved KPI results to %s", out_path)
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

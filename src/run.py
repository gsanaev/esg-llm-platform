import argparse
from esg_system.core.pdf_reader import extract_text
from esg_user.pipeline.extract_kpis import extract_all_kpis
from esg_user.pipeline.normalize_kpis import normalize_kpis
from esg_user.pipeline.assemble_output import assemble_output, export_to_json
from typing import Optional


def run_pipeline(pdf_path: str, output_path: Optional[str] = None) -> None:
    """
    Execute the full ESG extraction pipeline for a single PDF.
    """

    # 1. Load PDF text
    print(f"Reading PDF: {pdf_path}")
    text = extract_text(pdf_path)

    # 2. Extract raw KPIs
    print("Extracting raw KPIs...")
    raw_kpis = extract_all_kpis(text)

    # 3. Normalize KPI values and units
    print("Normalizing KPIs...")
    normalized = normalize_kpis(raw_kpis)

    # 4. Assemble final structured output
    print("Assembling final output...")
    final_output = assemble_output(normalized, source_pdf=pdf_path)

    # 5. Optional save as JSON
    if output_path:
        print(f"Saving output to {output_path}...")
        export_to_json(final_output, output_path)

    print("Pipeline completed.")


def main():
    parser = argparse.ArgumentParser(
        description="Run ESG KPI extraction pipeline on a PDF document."
    )

    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file to process."
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Optional path to save JSON output."
    )

    args = parser.parse_args()

    run_pipeline(args.pdf_path, args.output)


if __name__ == "__main__":
    main()

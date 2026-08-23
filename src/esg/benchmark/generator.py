from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esg.benchmark.truth import load_benchmark_truth


_METRIC_ORDER = (
    "total_ghg_emissions",
    "energy_consumption",
    "water_withdrawal",
)

_METRIC_LABELS = {
    "total_ghg_emissions": "Total GHG emissions",
    "energy_consumption": "Total energy consumption",
    "water_withdrawal": "Total water withdrawal",
}


def _invariant_canvas(*args: Any, **kwargs: Any) -> pdf_canvas.Canvas:
    """
    Build PDFs with stable ReportLab metadata for reproducible output.
    """
    kwargs["invariant"] = 1
    return pdf_canvas.Canvas(*args, **kwargs)


def _format_value(value: Any) -> str:
    """
    Format benchmark numeric values in a stable disclosure representation.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:,.0f}"
    return str(value)


def generate_company_pdf(
    company: Mapping[str, Any],
    output_dir: str | Path,
) -> Path:
    """
    Generate one deterministic synthetic ESG disclosure from benchmark truth.
    """
    company_id = str(company["company_id"])
    reporting_year = int(company["reporting_year"])
    metrics = company["metrics"]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_path = output_path / f"{company_id}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph(
            f"Synthetic ESG Disclosure – {company_id}",
            styles["Heading1"],
        ),
        Paragraph(
            f"Reporting year: {reporting_year}",
            styles["BodyText"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    rows = [["KPI", "Unit", str(reporting_year)]]

    for metric in _METRIC_ORDER:
        entry = metrics[metric]
        rows.append(
            [
                _METRIC_LABELS[metric],
                str(entry["unit"]),
                _format_value(entry["value"]),
            ]
        )

    table = Table(rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)
    doc.build(story, canvasmaker=_invariant_canvas)

    return pdf_path


def generate_benchmark_pdfs(
    truth_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """
    Generate one synthetic disclosure PDF for each benchmark company.
    """
    truth = load_benchmark_truth(truth_path)

    return [
        generate_company_pdf(company, output_dir)
        for company in truth["companies"]
    ]

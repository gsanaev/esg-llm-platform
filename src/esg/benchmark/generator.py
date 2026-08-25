from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from esg.benchmark.cases import load_benchmark_cases
from esg.benchmark.truth import load_benchmark_truth


_METRIC_ORDER = (
    "total_ghg_emissions",
    "energy_consumption",
    "water_withdrawal",
    "water_consumption",
    "water_stress_share",
    "water_dependency",
)

_METRIC_LABELS = {
    "total_ghg_emissions": "Total GHG emissions",
    "energy_consumption": "Total energy consumption",
    "water_withdrawal": "Total water withdrawal",
    "water_consumption": "Total water consumption",
    "water_stress_share": "Water stress share",
    "water_dependency": "Water dependency",
}

_NARRATIVE_TEMPLATES = {
    "total_ghg_emissions": (
        "In {year}, the company reported total GHG emissions "
        "of {value} {unit}."
    ),
    "energy_consumption": (
        "Total energy consumption for the same reporting year "
        "was {value} {unit}."
    ),
    "water_withdrawal": (
        "Total water withdrawal across operations "
        "was {value} {unit}."
    ),
    "water_consumption": (
        "Total water consumption across operations "
        "was {value} {unit}."
    ),
    "water_stress_share": (
        "The share of water use in water-stressed areas "
        "was {value} {unit}."
    ),
    "water_dependency": (
        "The company described its water dependency as {value}."
    )
}

# Disclosure-side conversions are deliberately independent from extraction
# normalization. Only conversions required by benchmark cases belong here.
_DISCLOSURE_UNIT_FACTORS = {
    ("energy_consumption", "MWh", "GWh"): 1 / 1000,
    ("water_stress_share", "fraction", "%"): 100,
}

_DEFAULT_DISCLOSURE_UNITS = {
    "water_stress_share": "%",
}


def _invariant_canvas(*args: Any, **kwargs: Any) -> pdf_canvas.Canvas:
    """
    Build PDFs with stable ReportLab metadata for reproducible output.
    """
    kwargs["invariant"] = 1
    return pdf_canvas.Canvas(*args, **kwargs)


def _format_value(
    value: Any,
    number_format: str = "en",
) -> str:
    """
    Format benchmark numeric values using a controlled disclosure format.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return str(value)

    formatted = f"{value:,.0f}"

    if number_format == "en":
        return formatted

    if number_format == "de":
        return formatted.replace(",", ".")

    raise ValueError(f"Unsupported number format: {number_format}")


def _prepare_disclosure_value(
    metric: str,
    entry: Mapping[str, Any],
    case: Mapping[str, Any],
) -> tuple[Any, str | None]:
    """
    Convert hidden truth into the unit requested by a disclosure case.

    This changes only the representation in the generated report.
    Hidden benchmark truth remains unchanged.
    """
    value = entry["value"]
    source_unit_raw = entry.get("unit")

    unit_overrides = case.get("unit_overrides") or {}

    if source_unit_raw is None:
        if metric in unit_overrides:
            raise ValueError(
                "Cannot override unit for unitless benchmark metric: "
                f"{metric}"
            )
        return value, None

    source_unit = str(source_unit_raw)
    default_unit = _DEFAULT_DISCLOSURE_UNITS.get(
        metric,
        source_unit,
    )
    target_unit = str(
        unit_overrides.get(metric, default_unit)
    )

    if target_unit == source_unit:
        return value, source_unit

    factor = _DISCLOSURE_UNIT_FACTORS.get(
        (metric, source_unit, target_unit)
    )

    if factor is None:
        raise ValueError(
            "Unsupported disclosure unit conversion: "
            f"{metric} {source_unit} -> {target_unit}"
        )

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(
            f"Cannot convert non-numeric benchmark value for {metric}."
        )

    return value * factor, target_unit


def _build_table(
    company: Mapping[str, Any],
    case: Mapping[str, Any],
) -> Table:
    reporting_year = int(company["reporting_year"])
    metrics = company["metrics"]
    number_format = str(case.get("number_format", "en"))

    rows = [["KPI", "Unit", str(reporting_year)]]

    for metric in _METRIC_ORDER:
        value, unit = _prepare_disclosure_value(
            metric,
            metrics[metric],
            case,
        )
        rows.append(
            [
                _METRIC_LABELS[metric],
                unit or "",
                _format_value(value, number_format),
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

    return table


def _build_narrative(
    company: Mapping[str, Any],
    case: Mapping[str, Any],
) -> list[Paragraph | Spacer]:
    reporting_year = int(company["reporting_year"])
    metrics = company["metrics"]
    number_format = str(case.get("number_format", "en"))
    styles = getSampleStyleSheet()

    story: list[Paragraph | Spacer] = []

    for metric in _METRIC_ORDER:
        value, unit = _prepare_disclosure_value(
            metric,
            metrics[metric],
            case,
        )

        text = _NARRATIVE_TEMPLATES[metric].format(
            year=reporting_year,
            value=_format_value(value, number_format),
            unit=unit,
        )

        story.append(Paragraph(text, styles["BodyText"]))
        story.append(Spacer(1, 0.35 * cm))

    return story


def generate_case_pdf(
    company: Mapping[str, Any],
    case: Mapping[str, Any],
    output_dir: str | Path,
) -> Path:
    """
    Generate one controlled synthetic disclosure benchmark case.
    """
    company_id = str(company["company_id"])
    case_id = str(case["case_id"])
    disclosure_format = str(case["disclosure_format"])
    output_filename = str(case["output_filename"])

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_path = output_path / output_filename

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
            f"Synthetic ESG Disclosure – {case_id}",
            styles["Heading1"],
        ),
        Paragraph(
            f"Company: {company_id}",
            styles["BodyText"],
        ),
        Paragraph(
            f"Reporting year: {company['reporting_year']}",
            styles["BodyText"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    if disclosure_format == "table":
        story.append(_build_table(company, case))
    elif disclosure_format == "narrative":
        story.extend(_build_narrative(company, case))
    else:
        raise ValueError(
            f"Unsupported disclosure format: {disclosure_format}"
        )

    doc.build(story, canvasmaker=_invariant_canvas)

    return pdf_path


def generate_benchmark_pdfs(
    truth_path: str | Path,
    cases_path: str | Path,
    output_dir: str | Path,
) -> list[Path]:
    """
    Generate controlled synthetic PDFs from hidden truth and case definitions.
    """
    truth = load_benchmark_truth(truth_path)
    cases = load_benchmark_cases(cases_path)

    companies = {
        str(company["company_id"]): company
        for company in truth["companies"]
    }

    generated: list[Path] = []

    for case in cases:
        company_id = str(case["company_id"])

        if company_id not in companies:
            raise ValueError(
                f"Unknown benchmark company_id: {company_id}"
            )

        generated.append(
            generate_case_pdf(
                companies[company_id],
                case,
                output_dir,
            )
        )

    return generated

# data/samples/make_samples.py
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
H = styles["Heading1"]
P = styles["BodyText"]


def _doc(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _kpi_table(values: list[list[str]]) -> Table:
    table = Table(values, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def make_esg_simple_text(path: Path) -> None:
    doc = _doc(path)
    story = [
        Paragraph("ESG Sample – Simple Text", H),
        Paragraph(
            "In 2024, the company reported total GHG emissions "
            "(tCO2e) of 123,400 across its Scope 1 and Scope 2 activities.",
            P,
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Total energy consumption (MWh) for the same period "
            "amounted to 500,000, including electricity and fuels.",
            P,
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Total water withdrawal (m3) across all operations "
            "was 1,200,000, including municipal and surface water sources.",
            P,
        ),
    ]

    doc.build(story)


def make_esg_simple_table(path: Path) -> None:
    doc = _doc(path)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions", "tCO2e", "123,400"],
        ["Total energy consumption", "MWh", "500,000"],
        ["Total water withdrawal", "m3", "1,200,000"],
    ]

    story = [
        Paragraph("ESG Sample – Simple Table", H),
        Spacer(1, 0.5 * cm),
        _kpi_table(data),
    ]

    doc.build(story)


def make_esg_simple_mixed(path: Path) -> None:
    doc = _doc(path)

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions (tCO2e)", "", "123,400"],
        ["Total energy consumption (MWh)", "", "500,000"],
        ["Total water withdrawal (m3)", "", "1,200,000"],
    ]

    story = [
        Paragraph("ESG Sample – Mixed Text + Table", H),
        Paragraph(
            "The following table summarises the company's core environmental "
            "KPIs for the reporting year 2024.",
            P,
        ),
        Spacer(1, 0.5 * cm),
        _kpi_table(data),
    ]

    doc.build(story)


def make_esg_nlp_test(path: Path) -> None:
    doc = _doc(path)

    story = [
        Paragraph(
            "Environmental, Social & Governance (ESG) "
            "Performance Summary — 2024",
            H,
        ),
        Paragraph(
            "This simplified ESG report provides an overview of the company's "
            "environmental performance for 2024. The information includes "
            "greenhouse gas emissions, energy consumption, and water "
            "withdrawal metrics.",
            P,
        ),
        Spacer(1, 0.4 * cm),
        Paragraph(
            "Our total GHG emissions for the reporting year amounted to "
            "123,400 tCO2e.",
            P,
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Total energy consumption reached 500,000 MWh in 2024.",
            P,
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(
            "Total water withdrawal for the year totaled 1,200,000 m³.",
            P,
        ),
    ]

    doc.build(story)


def main() -> None:
    print(f"Writing PDFs into: {SAMPLES_DIR}")

    generators = [
        ("esg_simple_text.pdf", make_esg_simple_text),
        ("esg_simple_table.pdf", make_esg_simple_table),
        ("esg_simple_mixed.pdf", make_esg_simple_mixed),
        ("esg_nlp_test.pdf", make_esg_nlp_test),
    ]

    for filename, generator in generators:
        print(f"Generating {filename} ...")
        generator(SAMPLES_DIR / filename)

    print("Done.")


if __name__ == "__main__":
    main()

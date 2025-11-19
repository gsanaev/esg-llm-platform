from __future__ import annotations

import os
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from dotenv import load_dotenv
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]  # .../esg-llm-platform
RAW_DIR = PROJECT_ROOT / "data" / "samples"
RAW_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
H = styles["Heading1"]
H2 = styles["Heading2"]
P = styles["BodyText"]


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _doc(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _kpi_table(values) -> Table:
    """
    values should be a list of rows.
    We’ll reuse similar structure to what your extractors expect.
    """
    tbl = Table(values, hAlign="LEFT")
    tbl.setStyle(
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
    return tbl


def _locale_variants_row(label: str, base_unit: str) -> List[List[str]]:
    """
    Return several rows for the same KPI with different numeric formats.
    """
    return [
        [label + " (tCO2e)", "123,400"],         # US style comma
        [label + " (tCO2e)", "123.400"],         # EU style dot
        [label + " (tCO2e)", "123 400"],         # space
        [label + " (tCO2e)", "1,200,000"],       # big number US
        [label + " (tCO2e)", "1.200.000"],       # big number EU
        [label + " (tCO2e)", "1 200 000"],       # big number space
    ]


def _ocr_noise(text: str) -> str:
    """
    Introduce mild OCR-like noise: extra spaces, weird spacing, etc.
    Nothing too crazy so extractors still have a chance.
    """
    return (
        text.replace("GHG", "G H G")
        .replace("energy", "ene rgy")
        .replace("water", "wa  ter")
    )


def _has_llm() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") and OpenAI is not None)


def _generate_llm_paragraphs(title: str, n_sections: int = 3) -> List[str]:
    """
    Optional LLM text generator for more realistic ESG narrative.
    If no key / no client, returns simple static text instead.
    """
    static = [
        "This report presents a summary of the company's environmental performance over the last fiscal year.",
        "The company has continued to implement energy efficiency measures and decarbonisation initiatives.",
        "Water management remains a strategic priority, with a focus on reduced withdrawals in high-stress regions.",
    ]
    if not _has_llm():
        return static

    client = OpenAI()
    prompt = f"""
    You are writing a concise ESG report summary titled '{title}'.
    Write {n_sections} short paragraphs (3–4 sentences each) describing:
    - greenhouse gas emissions trends,
    - energy consumption and efficiency measures,
    - water withdrawal and management.

    Use realistic corporate ESG language.
    Do NOT include bullet points or headings; just plain paragraphs.
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional ESG report writer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=600,
        )
        content = resp.choices[0].message.content or ""
    except Exception:
        # Fallback to static if anything fails
        return static

    # Split into paragraphs by blank lines or double newline
    chunks = [p.strip() for p in content.split("\n\n") if p.strip()]
    return chunks[:n_sections] or static


# ---------------------------------------------------------------------
# Individual PDF generators
# ---------------------------------------------------------------------

def make_esg_simple_text(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Simple Text", H))

    story.append(
        Paragraph(
            "In 2024, the company reported total GHG emissions "
            "(tCO2e) of 123,400 across its Scope 1 and Scope 2 activities.",
            P,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            "Total energy consumption (MWh) for the same period "
            "amounted to 500,000, including electricity and fuels.",
            P,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            "Total water withdrawal (m3) across all operations "
            "was 1,200,000, including municipal and surface water sources.",
            P,
        )
    )

    doc.build(story)


def make_esg_simple_table(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Simple Table", H))
    story.append(Spacer(1, 0.5 * cm))

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions", "tCO2e", "123,400"],
        ["Total energy consumption", "MWh", "500,000"],
        ["Total water withdrawal", "m3", "1,200,000"],
    ]

    story.append(_kpi_table(data))
    doc.build(story)


def make_esg_simple_mixed(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Mixed Text + Table", H))

    story.append(
        Paragraph(
            "The following table summarises the company's core environmental KPIs "
            "for the reporting year 2024.",
            P,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions (tCO2e)", "", "123,400"],
        ["Total energy consumption (MWh)", "", "500,000"],
        ["Total water withdrawal (m3)", "", "1,200,000"],
    ]
    story.append(_kpi_table(data))

    story.append(Spacer(1, 0.75 * cm))

    story.append(
        Paragraph(
            "Performance improved compared to the previous year, "
            "with a modest reduction in emissions intensity.",
            P,
        )
    )

    doc.build(story)


def make_esg_locale_numbers(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Locale Number Variants", H))
    story.append(Spacer(1, 0.5 * cm))

    rows = [["KPI", "Value"]]
    rows += _locale_variants_row("Total GHG emissions", "tCO2e")

    story.append(_kpi_table(rows))
    story.append(Spacer(1, 0.75 * cm))

    story.append(
        Paragraph(
            "These rows demonstrate various locale-specific number formats "
            "for the same KPI. All refer to total GHG emissions (tCO2e).",
            P,
        )
    )

    doc.build(story)


def make_esg_messy_units(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Messy Units", H))
    story.append(Spacer(1, 0.5 * cm))

    data = [
        ["KPI", "Unit", "Value"],
        ["Total GHG emissions", "t CO2e", "123,400"],
        ["Total energy consumption", "M W h", "500,000"],
        ["Total water withdrawal", "m³", "1,200,000"],
    ]
    story.append(_kpi_table(data))

    story.append(Spacer(1, 0.75 * cm))
    story.append(
        Paragraph(
            "Units are intentionally formatted inconsistently (spaces, "
            "superscripts) to exercise normalization logic.",
            P,
        )
    )

    doc.build(story)


def make_esg_unstructured_long(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Unstructured Long Text", H))

    paragraphs = [
        (
            "Throughout the reporting year, the organisation advanced multiple "
            "initiatives aimed at decarbonising its operations. In 2024, "
            "total GHG emissions (tCO2e) reached 123,400, reflecting a "
            "modest change compared to the previous year."
        ),
        (
            "Energy consumption (MWh) remained relatively stable at 500,000, "
            "with a gradual shift towards renewable electricity sourcing. "
            "The company invested in energy efficiency measures in production "
            "facilities and office locations."
        ),
        (
            "Total water withdrawal (m3) amounted to 1,200,000, with ongoing "
            "efforts to reduce abstraction from water-stressed regions. "
            "Operational teams continue to monitor water performance "
            "through site-level metrics and internal dashboards."
        ),
        (
            "The narrative format and dispersed KPI references are intended "
            "to test sentence-based extraction capabilities rather than "
            "structured table logic."
        ),
    ]

    for p in paragraphs:
        story.append(Paragraph(p, P))
        story.append(Spacer(1, 0.4 * cm))

    doc.build(story)


def make_esg_ocr_noise(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – OCR-like Noise", H))

    base = (
        "In 2024 the company reported Total GHG emissions (tCO2e) of 123,400; "
        "Total energy consumption (MWh) of 500,000; and Total water withdrawal "
        "(m3) of 1,200,000 across its operations."
    )
    noisy = _ocr_noise(base)

    story.append(Paragraph(noisy, P))
    story.append(Spacer(1, 0.5 * cm))

    story.append(
        Paragraph(
            "This paragraph includes intentional spacing distortions to simulate OCR noise.",
            P,
        )
    )

    doc.build(story)


def make_esg_corrupted_table(path: Path) -> None:
    doc = _doc(path)
    story = []

    story.append(Paragraph("ESG Sample – Corrupted / Partial Table", H))
    story.append(Spacer(1, 0.5 * cm))

    data = [
        ["KPI", "Unit", "2024"],
        ["Total GHG emissions (tCO2e)", "", "123,400"],
        ["Total energy consumption", "", "500,000"],  # missing unit cell
        ["Total water withdrawal (m3)", None, "1,200,000"],  # None unit
        ["Other KPI", "N/A", ""],  # empty value
    ]
    story.append(_kpi_table(data))

    story.append(Spacer(1, 0.75 * cm))
    story.append(
        Paragraph(
            "Some cells are intentionally left blank or set to None to simulate "
            "imperfect table extraction.",
            P,
        )
    )

    doc.build(story)


def make_esg_llm_realistic_1(path: Path) -> None:
    doc = _doc(path)
    story = []

    title = "ESG Sample – LLM Realistic Report 1"
    story.append(Paragraph(title, H))

    paragraphs = _generate_llm_paragraphs(title, n_sections=3)
    for p in paragraphs:
        story.append(Paragraph(p, P))
        story.append(Spacer(1, 0.4 * cm))

    # Ensure KPIs appear explicitly at least once
    story.append(
        Paragraph(
            "For clarity, key metrics for 2024 are: "
            "total GHG emissions (tCO2e) 123,400; "
            "total energy consumption (MWh) 500,000; "
            "total water withdrawal (m3) 1,200,000.",
            P,
        )
    )

    doc.build(story)


def make_esg_llm_realistic_2(path: Path) -> None:
    doc = _doc(path)
    story = []

    title = "ESG Sample – LLM Realistic Report 2"
    story.append(Paragraph(title, H))

    paragraphs = _generate_llm_paragraphs(title, n_sections=4)
    for p in paragraphs:
        story.append(Paragraph(p, P))
        story.append(Spacer(1, 0.4 * cm))

    doc.build(story)


# ---------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------

def main() -> None:
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Writing PDFs into: {RAW_DIR}")

    generators = [
        ("esg_simple_text.pdf", make_esg_simple_text),
        ("esg_simple_table.pdf", make_esg_simple_table),
        ("esg_simple_mixed.pdf", make_esg_simple_mixed),
        ("esg_locale_numbers.pdf", make_esg_locale_numbers),
        ("esg_messy_units.pdf", make_esg_messy_units),
        ("esg_unstructured_long.pdf", make_esg_unstructured_long),
        ("esg_ocr_noise.pdf", make_esg_ocr_noise),
        ("esg_corrupted_table.pdf", make_esg_corrupted_table),
    ]

    for filename, fn in generators:
        path = RAW_DIR / filename
        print(f"Generating {filename} ...")
        fn(path)

    # LLM-based ones (optional)
    if _has_llm():
        print("OPENAI_API_KEY detected – generating LLM-based PDFs...")
        llm_generators = [
            ("esg_llm_realistic_1.pdf", make_esg_llm_realistic_1),
            ("esg_llm_realistic_2.pdf", make_esg_llm_realistic_2),
        ]
        for filename, fn in llm_generators:
            path = RAW_DIR / filename
            print(f"Generating {filename} ...")
            fn(path)
    else:
        print("No OPENAI_API_KEY found – skipping LLM-based PDFs.")

    print("Done.")


if __name__ == "__main__":
    main()

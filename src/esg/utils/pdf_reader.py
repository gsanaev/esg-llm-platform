from __future__ import annotations

import logging
from pathlib import Path
import pdfplumber

logger = logging.getLogger(__name__)


def extract_text(pdf_path: str) -> str:
    """
    Minimal text extraction used by ESG V2 pipeline.
    Returns cleaned concatenated text from all PDF pages.
    """
    path = Path(pdf_path)

    if not path.exists():
        logger.error("PDF not found: %s", pdf_path)
        return ""

    pages = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    logger.warning("Failed to extract page %s: %s", i, exc)
                    text = ""
                pages.append(text)
    except Exception as exc:
        logger.error("Failed to open PDF %s: %s", pdf_path, exc)
        return ""

    # No external text_cleaner — minimal normalization:
    raw = "\n\n".join(pages)
    cleaned = " ".join(raw.split())
    return cleaned

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import pdfplumber

from .text_cleaner import clean_text

logger = logging.getLogger(__name__)


def _read_pages(pdf_path: Path) -> List[str]:
    """Extract raw text from each page using pdfplumber."""
    pages_text: List[str] = []

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception as e:  # pragma: no cover
                    logger.warning("Failed to extract text from page %s: %s", i, e)
                    text = ""
                pages_text.append(text)
    except Exception as e:
        logger.error("Failed to open PDF '%s': %s", pdf_path, e)
        return []

    return pages_text


def extract_text(pdf_path: str) -> str:
    """
    Extract full text from a PDF and apply basic cleaning.

    Returns a single string containing the concatenated page texts.
    """
    path = Path(pdf_path)

    if not path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        return ""

    pages_text = _read_pages(path)
    raw = "\n\n".join(pages_text)

    cleaned = clean_text(raw)
    logger.debug("Extracted %d characters of cleaned text from %s", len(cleaned), pdf_path)

    return cleaned

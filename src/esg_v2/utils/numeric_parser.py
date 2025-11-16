# src/esg_v2/utils/numeric_parser.py
from __future__ import annotations
import re

MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "billion": 1_000_000_000,
}

def parse_number(text: str):
    if text is None:
        return None

    s = text.strip().lower()

    # Remove thousand separators
    s = s.replace(",", "").replace(" ", "")

    # Try plain float first (captures scientific notation)
    try:
        return float(s)
    except ValueError:
        pass

    # Find number + multiplier
    pattern = r"([0-9]*\.?[0-9]+)\s*(k|m|b|thousand|million|billion)?"
    m = re.search(pattern, s)

    if not m:
        return None

    num_str, mult_str = m.groups()
    num = float(num_str)

    if mult_str:
        num *= MULTIPLIERS[mult_str]

    return num

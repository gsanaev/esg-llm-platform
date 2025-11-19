from __future__ import annotations

import re
from typing import Optional


def parse_locale_number(num: Optional[str]) -> Optional[float]:
    """
    Locale-aware numeric parser used by all normalizers:
    - 123,400
    - 123.400
    - 123 400
    - 1,200,000
    - 1.200.000
    - 1 200 000
    - 123.45
    - 123,45
    """
    if not num:
        return None

    s = num.strip().replace("\u00A0", " ")
    if not s:
        return None

    s_no_space = s.replace(" ", "")

    # Thousands grouping: 1,200,000 or 1.200.000
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        try:
            return float(re.sub(r"[.,]", "", s_no_space))
        except Exception:
            return None

    # Thousands grouping with spaces: 1 200 000
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        try:
            return float(s.replace(" ", ""))
        except Exception:
            return None

    # Integer
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # Decimal: 123.45 or 123,45
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # Fallback: strip separators
    cleaned = re.sub(r"[ ,\.]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return None


def parse_scaled_number(raw: Optional[str]) -> Optional[float]:
    """
    Parse scaled numbers:
    - "1.2 million"
    - "1.2 thousand"
    - "120k"
    """
    if not raw:
        return None

    s = raw.strip()
    if not s:
        return None

    s_lower = s.lower().replace("\u00A0", " ")

    scale = 1.0
    if "million" in s_lower:
        scale = 1_000_000
    elif "thousand" in s_lower:
        scale = 1_000
    elif s_lower.endswith("k"):
        scale = 1_000

    # Remove scale words
    s_clean = re.sub(r"(million|thousand|k)", "", s_lower)

    num = parse_locale_number(s_clean)
    if num is None:
        return None

    return num * scale

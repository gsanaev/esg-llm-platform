from __future__ import annotations

import re
from typing import Optional


# All known whitespace variants (regular + non-breaking)
SPACE_CHARS = [
    "\u0020",  # normal space
    "\u00A0",  # NBSP
    "\u2007",  # figure space
    "\u202F",  # narrow NBSP
]


def _normalize_spaces(s: str) -> str:
    """Replace all types of weird spaces with a normal space."""
    for ch in SPACE_CHARS:
        s = s.replace(ch, " ")
    return s


def parse_locale_number(num: Optional[str]) -> Optional[float]:
    """
    Robust locale-aware numeric parser.

    Handles:
      - 123,400
      - 123.400
      - 1,200,000
      - 1.200.000
      - 1 200 000
      - 1200000.
      - 123.45
      - 123,45
      - UTF-8 spaces: 1 200 000, 1 200 000.0
    """
    if not num:
        return None

    s = _normalize_spaces(num.strip())
    if not s:
        return None

    # -- Remove trailing dots like "1200000." --
    s = s.rstrip(".")

    # Remove internal spaces
    s_no_space = s.replace(" ", "")

    # Case 1 — grouped thousands: 1,200,000 or 1.200.000
    if re.match(r"^\d{1,3}([.,]\d{3})+$", s_no_space):
        try:
            return float(re.sub(r"[.,]", "", s_no_space))
        except Exception:
            return None

    # Case 2 — spaced thousands: 1 200 000
    if re.match(r"^\d{1,3}( \d{3})+$", s):
        try:
            return float(s.replace(" ", ""))
        except Exception:
            return None

    # Case 3 — integer
    if re.match(r"^\d+$", s_no_space):
        try:
            return float(s_no_space)
        except Exception:
            return None

    # Case 4 — decimal: 123.45 or 123,45
    if re.match(r"^\d+[.,]\d+$", s_no_space):
        try:
            return float(s_no_space.replace(",", "."))
        except Exception:
            return None

    # Case 5 — weird formats with mixed separators
    cleaned = re.sub(r"[ ,\.]", "", s)
    try:
        return float(cleaned)
    except Exception:
        return None


def parse_scaled_number(raw: Optional[str]) -> Optional[float]:
    """
    Parse scaled numbers:
      - "1.2 million"
      - "1,2 million" (EU)
      - "1.2 million" (NBSP)
      - "120k"
    """
    if not raw:
        return None

    s = _normalize_spaces(raw.strip().lower())
    if not s:
        return None

    scale = 1.0
    if "million" in s:
        scale = 1_000_000
    elif "billion" in s:
        scale = 1_000_000_000
    elif "thousand" in s:
        scale = 1_000
    elif s.endswith("k"):
        scale = 1_000

    # Remove scale words and "k"
    s_clean = re.sub(r"(million|billion|thousand|k)", "", s)

    num = parse_locale_number(s_clean)
    if num is None:
        return None

    return num * scale

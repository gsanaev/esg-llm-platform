# src/esg_v2/normalization/regex_normalizer.py
from __future__ import annotations

import logging
import re
from typing import Any, Dict

from esg_v2.utils.numeric_parser import parse_number

logger = logging.getLogger(__name__)

# Simple pattern for a single numeric token (with optional decimal / comma)
_NUMBER_TOKEN = re.compile(r"[+-]?\d+(?:[.,]\d+)?")

def _has_single_numeric_token(s: str) -> bool:
    """
    Return True if the string contains exactly ONE numeric token.

    This is used to avoid trying to parse table-like strings such as:
        "23 23.6 61.7 18,537 15,849 million"
    which clearly contain multiple numbers and should not be collapsed
    into a single numeric value.
    """
    tokens = _NUMBER_TOKEN.findall(s)
    return len(tokens) == 1


def normalize_regex_result_v2(
    regex_res: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize v2 regex extractor output.

    Input format (per KPI):
        {
            "raw_value": "123,400" or "1.2 million",
            "raw_unit": "tCO2e" / "MWh" / "m3",
            "confidence": float,
            # optional: "value": already numeric
        }

    Output:
        Same dict, but with a cleaned "value" (float) where possible.

    Rules:
    - If 'value' is already numeric and < 1e9, keep it as-is.
    - Otherwise, try to parse 'raw_value' with parse_number.
    - If 'raw_value' contains MULTIPLE numeric tokens, we treat it as
      a bad candidate (likely a whole row) and leave value=None so that
      downstream fusion can fall back to v1.
    """
    cleaned: Dict[str, Dict[str, Any]] = {}

    for kpi, entry in regex_res.items():
        # Start from a shallow copy so we don't mutate the input
        new_entry = dict(entry)

        # If there's already a reasonable numeric value, keep it
        existing_value = new_entry.get("value")
        if isinstance(existing_value, (int, float)) and existing_value < 1e9:
            cleaned[kpi] = new_entry
            continue

        raw_val = new_entry.get("raw_value")
        if raw_val is None:
            # Nothing we can parse
            new_entry.setdefault("value", None)
            cleaned[kpi] = new_entry
            continue

        raw_str = " ".join(str(raw_val).split())  # normalize whitespace

        # --- Multi-number guard: reject table-like rows -----------------
        if not _has_single_numeric_token(raw_str):
            logger.warning(
                "normalize_regex_result_v2: multiple numeric tokens in raw_value "
                "'%s' for KPI '%s'; skipping numeric parse and falling back.",
                raw_str,
                kpi,
            )
            # Leave value as None; pipeline fusion will fall back to v1
            new_entry["value"] = None
            cleaned[kpi] = new_entry
            continue

        # --- Safe to parse: exactly one numeric token -------------------
        parsed = parse_number(raw_str)

        if parsed is None:
            logger.warning(
                "normalize_regex_result_v2: could not parse raw_value '%s' for KPI "
                "'%s'; leaving value=None so v1 can be used.",
                raw_str,
                kpi,
            )
            new_entry["value"] = None
        else:
            new_entry["value"] = parsed

        cleaned[kpi] = new_entry

    return cleaned

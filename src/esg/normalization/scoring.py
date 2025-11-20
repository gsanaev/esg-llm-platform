# src/esg/normalization/scoring.py
from __future__ import annotations

from typing import Any, Iterable, Optional


def compute_extraction_score(
    *,
    parsed_value: Optional[float],
    raw_value: Optional[str],
    unit: Optional[str],
    allowed_units: Iterable[str],
    base_confidence: float,
    source: str,
) -> dict[str, Any]:
    """
    Lightweight internal scoring helper.

    This does NOT change the public `confidence` field used in tests and API.
    Instead, it returns a small debug dict that can be attached under `_score`
    in the normalized results.

    Heuristics (very simple on purpose):
      - value_quality: 1.0 if parsed_value is not None, else 0.0
      - unit_quality:
          * 1.0 if unit is in allowed_units
          * 0.7 if allowed_units is empty but we have some unit
          * 0.0 otherwise
      - source_weight: small prior per source type

    Final score is:
        score = base_confidence * (0.7 * value_quality + 0.3 * unit_quality) * source_weight
    """

    allowed_units = list(allowed_units or [])
    has_value = parsed_value is not None

    # ----- value quality -----
    value_quality = 1.0 if has_value else 0.0

    # ----- unit quality -----
    if unit and allowed_units:
        unit_quality = 1.0 if unit in allowed_units else 0.0
    elif unit and not allowed_units:
        unit_quality = 0.7  # we have a unit, but no schema guidance
    else:
        unit_quality = 0.0

    # ----- source priors -----
    # These are deliberately mild; they do NOT affect confidence,
    # only this internal diagnostic score.
    source_priors = {
        "table_grid": 1.05,
        "table_plain": 1.0,
        "regex": 0.95,
        "nlp": 0.9,
        "llm": 0.85,
        "unknown": 1.0,
    }
    source_weight = source_priors.get(source, source_priors["unknown"])

    raw_term = 0.7 * value_quality + 0.3 * unit_quality

    score = base_confidence * raw_term * source_weight

    # Clamp to [0, 1] just for sanity
    score = max(0.0, min(1.0, score))

    return {
        "value_quality": value_quality,
        "unit_quality": unit_quality,
        "source_weight": source_weight,
        "base_confidence": base_confidence,
        "score": score,
    }

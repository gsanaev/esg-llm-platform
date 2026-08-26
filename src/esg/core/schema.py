# src/esg/core/schema.py

from __future__ import annotations

from typing import Any, Mapping


def get_accepted_units(meta: Mapping[str, Any]) -> list[str]:
    """Return the unit representations accepted for a KPI."""
    return list(meta.get("accepted_units") or [])


def get_canonical_unit(meta: Mapping[str, Any]) -> str | None:
    """Return the canonical normalized unit for a KPI."""
    canonical = meta.get("canonical_unit")
    return str(canonical) if canonical else None


def get_synonyms(code: str, meta: Mapping[str, Any]) -> list[str]:
    """
    Return controlled metric-identification phrases.

    Prefer explicit synonyms and fall back to the humanized KPI code
    when synonyms are unavailable.
    """
    synonyms = meta.get("synonyms")
    if synonyms:
        return list(synonyms)

    return [code.replace("_", " ")]

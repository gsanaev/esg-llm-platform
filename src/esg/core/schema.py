# src/esg/core/schema.py

from __future__ import annotations

from typing import Any, Mapping


def get_accepted_units(meta: Mapping[str, Any]) -> list[str]:
    """
    Return the unit representations accepted for a KPI.

    Supports the current v1 `units` field and the planned v2
    `accepted_units` field during schema migration.
    """
    units = meta.get("accepted_units")
    if units is None:
        units = meta.get("units")

    return list(units or [])


def get_canonical_unit(meta: Mapping[str, Any]) -> str | None:
    """
    Return the canonical normalized unit for a KPI.

    v2 schemas should provide `canonical_unit` explicitly.
    During migration, fall back to the first entry in the
    legacy `units` field.
    """
    canonical = meta.get("canonical_unit")
    if canonical:
        return str(canonical)

    units = get_accepted_units(meta)
    return units[0] if units else None


def get_synonyms(code: str, meta: Mapping[str, Any]) -> list[str]:
    """
    Return controlled metric-identification phrases.

    Prefer explicit `synonyms`. During migration, fall back to
    `keywords`, then finally to the humanized KPI code.
    """
    synonyms = meta.get("synonyms")
    if synonyms:
        return list(synonyms)

    keywords = meta.get("keywords")
    if keywords:
        return list(keywords)

    return [code.replace("_", " ")]
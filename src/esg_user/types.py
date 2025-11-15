from __future__ import annotations

from typing import Any, Optional, List, TypedDict


class ExtractorResult(TypedDict, total=False):
    """
    Strict type definition for static analysis.  
    This describes the *fields* that every extractor result may contain.
    """
    value: Optional[float]
    unit: Optional[str]
    confidence: float
    source: List[str]
    raw_value: Any
    raw_unit: Any


class ExtractorResultDict(dict[str, Any]):
    """
    Runtime implementation of ExtractorResult.  
    Behaves like a dict, but is typed so Pylance accepts assignments,
    indexing, `.get()`, and returning it from functions.
    """

    # These attributes are here only to guide static type checking.
    value: Optional[float]
    unit: Optional[str]
    confidence: float
    source: List[str]
    raw_value: Any
    raw_unit: Any

    def __init__(
        self,
        value: Any = None,
        unit: Optional[str] = None,
        confidence: float = 0.0,
        source: Optional[List[str]] = None,
        raw_value: Any = None,
        raw_unit: Any = None,
    ) -> None:

        super().__init__()
        self["value"] = value
        self["unit"] = unit
        self["confidence"] = float(confidence)
        self["source"] = source or []
        self["raw_value"] = raw_value if raw_value is not None else value
        self["raw_unit"] = raw_unit if raw_unit is not None else unit


def make_result(
    value: Any = None,
    unit: Optional[str] = None,
    confidence: float = 0.0,
    source: Optional[List[str]] = None,
    raw_value: Any = None,
    raw_unit: Any = None,
) -> ExtractorResultDict:
    """
    Factory that always returns a dict-like ExtractorResult object.
    """
    return ExtractorResultDict(
        value=value,
        unit=unit,
        confidence=confidence,
        source=source,
        raw_value=raw_value,
        raw_unit=raw_unit,
    )

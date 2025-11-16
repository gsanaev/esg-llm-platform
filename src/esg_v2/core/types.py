# src/esg_v2/core/types.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class KPIResult:
    """
    Canonical KPI representation used by the v2 pipeline.

    This is intentionally simple and decoupled from internal extractor types.
    """
    code: str
    value: Optional[float]
    unit: Optional[str]
    confidence: float
    source: List[str]  # e.g. ["regex", "table_fitz"]

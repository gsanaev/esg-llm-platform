# src/esg/core/types.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class EvidenceCandidate:
    """
    One extracted piece of evidence for a sustainability metric.

    Evidence candidates preserve raw and normalized observations together
    with provenance. They are intentionally distinct from final KPI results:
    reconciliation and acceptance happen later in the pipeline.

    `page` is the 1-based PDF page number when available.
    """

    metric: str
    source_document: str
    extraction_method: str

    company_id: Optional[str] = None
    value_raw: Optional[str] = None
    value_normalized: Optional[float | str] = None
    unit_raw: Optional[str] = None
    unit_normalized: Optional[str] = None
    year: Optional[int] = None
    location: Optional[str] = None
    page: Optional[int] = None
    source_context: Optional[str] = None
    extraction_score: Optional[float] = None


@dataclass
class KPIResult:
    """
    Canonical KPI representation used by the current pipeline.

    This remains separate from EvidenceCandidate. In v2, final KPI results
    will eventually be produced after evidence reconciliation.
    """

    code: str
    value: Optional[float]
    unit: Optional[str]
    confidence: float
    source: List[str]
    status: Optional[str] = None
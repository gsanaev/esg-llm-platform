# src/esg/core/types.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional


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

ResultStatus = Literal[
    "accepted",
    "review_required",
    "not_reported",
]


@dataclass(frozen=True)
class ReconciledKPIResult:
    """
    Final KPI result produced after evidence reconciliation.

    This model is distinct from EvidenceCandidate and from the compact
    KPIResult representation used by the extraction/fusion API.
    """

    metric: str
    value: Optional[float | str]
    unit: Optional[str]

    supporting_evidence: tuple[EvidenceCandidate, ...] = field(
        default_factory=tuple
    )
    year: Optional[int] = None
    location: Optional[str] = None
    conflict_flag: bool = False
    review_required: bool = False
    status: ResultStatus = "not_reported"

    def __post_init__(self) -> None:
        if self.status not in {
            "accepted",
            "review_required",
            "not_reported",
        }:
            raise ValueError(f"Unsupported result status: {self.status}")

        if self.value is not None and self.status == "not_reported":
            raise ValueError(
                "A result with a value cannot have status 'not_reported'."
            )

        if self.status == "accepted" and self.review_required:
            raise ValueError(
                "An accepted result cannot require review."
            )

        if self.status == "review_required" and not self.review_required:
            raise ValueError(
                "Status 'review_required' requires review_required=True."
            )

@dataclass
class KPIResult:
    """
    Compact KPI representation used by the extraction/fusion API.

    Evidence-based final workflow decisions are represented separately by
    ReconciledKPIResult after evidence reconciliation.
    """

    code: str
    value: Optional[float | str]
    unit: Optional[str]
    confidence: float
    source: List[str]
    status: Optional[str] = None

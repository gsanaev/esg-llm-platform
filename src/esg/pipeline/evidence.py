# src/esg/pipeline/evidence.py

from __future__ import annotations

from typing import Any, Callable, Mapping

from esg.core.types import EvidenceCandidate


def normalized_results_to_evidence(
    normalized: Mapping[str, Mapping[str, Any]],
    *,
    source_document: str,
    extraction_method: str,
) -> list[EvidenceCandidate]:
    """
    Convert normalized extractor output into auditable evidence candidates.

    Page, source context, company, year, and location remain unset when the
    current extractor does not provide them. They must not be inferred.
    """
    evidence: list[EvidenceCandidate] = []

    for metric, entry in normalized.items():
        if not entry:
            continue

        score_data = entry.get("_score") or {}

        evidence.append(
            EvidenceCandidate(
                metric=metric,
                source_document=source_document,
                extraction_method=extraction_method,
                value_raw=entry.get("raw_value"),
                value_normalized=entry.get("value"),
                unit_raw=entry.get("raw_unit"),
                unit_normalized=entry.get("unit"),
                extraction_score=score_data.get("score"),
                page=entry.get("page"),
                source_context=entry.get("source_context"),
            )
        )

    return evidence


def raw_candidate_results_to_evidence(
    raw_candidates: Mapping[str, list[Mapping[str, Any]]],
    *,
    kpi_schema: Mapping[str, Any],
    normalizer: Callable[
        [
            dict[str, dict[str, Any]],
            Mapping[str, Any],
        ],
        Mapping[str, Mapping[str, Any]],
    ],
    source_document: str,
    extraction_method: str,
) -> list[EvidenceCandidate]:
    """
    Normalize plural raw extractor candidates one observation at a time
    and convert them into auditable EvidenceCandidate objects.

    Existing single-result normalizers are reused unchanged.
    Candidate order is preserved.
    """
    evidence: list[EvidenceCandidate] = []

    for metric, entries in raw_candidates.items():
        for entry in entries:
            normalized = normalizer(
                {metric: dict(entry)},
                kpi_schema,
            )

            evidence.extend(
                normalized_results_to_evidence(
                    normalized,
                    source_document=source_document,
                    extraction_method=extraction_method,
                )
            )

    return evidence

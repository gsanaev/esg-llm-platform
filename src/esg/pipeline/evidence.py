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
                company_id=entry.get("company_id"),
                value_raw=entry.get("raw_value"),
                value_normalized=entry.get("value"),
                unit_raw=entry.get("raw_unit"),
                unit_normalized=entry.get("unit"),
                year=entry.get("year"),
                location=entry.get("location"),
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

            normalized_entry = normalized.get(metric)

            if not normalized_entry:
                continue

            merged_entry = dict(normalized_entry)

            for field in (
                "company_id",
                "year",
                "location",
                "page",
                "source_context",
            ):
                if (
                    merged_entry.get(field) is None
                    and entry.get(field) is not None
                ):
                    merged_entry[field] = entry.get(field)

            evidence.extend(
                normalized_results_to_evidence(
                    {metric: merged_entry},
                    source_document=source_document,
                    extraction_method=extraction_method,
                )
            )

    return evidence

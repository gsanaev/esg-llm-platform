# src/esg/pipeline/reconciliation.py

from __future__ import annotations

from math import isclose
from typing import Sequence

from esg.core.types import EvidenceCandidate, ReconciledKPIResult


def _values_agree(values: list[float | str]) -> bool:
    """Return True when normalized values agree."""
    if not values:
        return False

    first = values[0]

    for other in values[1:]:
        if isinstance(first, (int, float)) and isinstance(other, (int, float)):
            if not isclose(
                float(first),
                float(other),
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False
        elif first != other:
            return False

    return True


def _has_same_context_value_conflict(
    evidence: Sequence[EvidenceCandidate],
) -> bool:
    """
    Return True when values disagree within a sufficiently known
    reporting context.

    If some evidence provides a year or location, observations missing
    that dimension are not used to prove a same-context conflict. This
    prevents lost context from collapsing distinct observations into one
    artificial group.
    """
    known_year_exists = any(
        candidate.year is not None
        for candidate in evidence
    )
    known_location_exists = any(
        candidate.location is not None
        for candidate in evidence
    )

    grouped_values: dict[
        tuple[int | None, str | None, str | None],
        list[float | str],
    ] = {}

    for candidate in evidence:
        value = candidate.value_normalized

        if value is None:
            continue

        if (
            known_year_exists
            and candidate.year is None
        ):
            continue

        if (
            known_location_exists
            and candidate.location is None
        ):
            continue

        context = (
            candidate.year,
            candidate.location,
            candidate.unit_normalized,
        )

        grouped_values.setdefault(
            context,
            [],
        ).append(value)

    return any(
        len(values) > 1
        and not _values_agree(values)
        for values in grouped_values.values()
    )


def reconcile_metric_evidence(
    metric: str,
    evidence: Sequence[EvidenceCandidate],
) -> ReconciledKPIResult:
    """
    Reconcile evidence for one KPI into a final candidate result.

    Rules are intentionally conservative:
      - no evidence -> not_reported
      - evidence with no usable normalized value -> review_required
      - different known years or locations -> contextual review, not conflict
      - incompatible normalized units -> conflict
      - same-context value disagreement -> conflict
      - LLM-only evidence -> review_required
      - agreeing deterministic evidence -> accepted
    """
    matching = [
        candidate
        for candidate in evidence
        if candidate.metric == metric
    ]

    if not matching:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=None,
            status="not_reported",
        )

    supporting_evidence = tuple(matching)

    usable = [
        candidate
        for candidate in matching
        if candidate.value_normalized is not None
    ]

    if not usable:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=None,
            supporting_evidence=supporting_evidence,
            conflict_flag=False,
            review_required=True,
            status="review_required",
        )

    known_years = {
        candidate.year
        for candidate in usable
        if candidate.year is not None
    }
    known_locations = {
        candidate.location
        for candidate in usable
        if candidate.location is not None
    }
    known_units = {
        candidate.unit_normalized
        for candidate in usable
        if candidate.unit_normalized is not None
    }

    resolved_year = (
        next(iter(known_years))
        if len(known_years) == 1
        else None
    )
    resolved_location = (
        next(iter(known_locations))
        if len(known_locations) == 1
        else None
    )
    resolved_unit = (
        next(iter(known_units))
        if len(known_units) == 1
        else None
    )
    year_ambiguous = bool(known_years) and any(
        candidate.year is None
        for candidate in usable
    )
    location_ambiguous = bool(known_locations) and any(
        candidate.location is None
        for candidate in usable
    )

    same_context_value_conflict = (
        _has_same_context_value_conflict(usable)
    )

    if same_context_value_conflict:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=resolved_unit,
            supporting_evidence=supporting_evidence,
            year=None if year_ambiguous else resolved_year,
            location=(
                None
                if location_ambiguous
                else resolved_location
            ),
            conflict_flag=True,
            review_required=True,
            status="review_required",
        )

    # Different known reporting contexts are not automatically conflicts.
    if len(known_years) > 1 or len(known_locations) > 1:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=resolved_unit,
            supporting_evidence=supporting_evidence,
            year=None,
            location=None,
            conflict_flag=False,
            review_required=True,
            status="review_required",
        )

    # Mixed known/unknown context is ambiguous rather than conflicting.

    # More than one normalized unit for the same comparable KPI is a conflict.
    if len(known_units) > 1:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=None,
            supporting_evidence=supporting_evidence,
            year=resolved_year,
            location=resolved_location,
            conflict_flag=True,
            review_required=True,
            status="review_required",
        )

    unit_ambiguous = bool(known_units) and any(
        candidate.unit_normalized is None
        for candidate in usable
    )

    values = [
        candidate.value_normalized
        for candidate in usable
        if candidate.value_normalized is not None
    ]

    values_agree = _values_agree(values)

    if year_ambiguous or location_ambiguous or unit_ambiguous:
        return ReconciledKPIResult(
            metric=metric,
            value=values[0] if values_agree else None,
            unit=resolved_unit,
            supporting_evidence=supporting_evidence,
            year=None if year_ambiguous else resolved_year,
            location=None if location_ambiguous else resolved_location,
            conflict_flag=False,
            review_required=True,
            status="review_required",
        )

    if not values_agree:
        return ReconciledKPIResult(
            metric=metric,
            value=None,
            unit=resolved_unit,
            supporting_evidence=supporting_evidence,
            year=resolved_year,
            location=resolved_location,
            conflict_flag=True,
            review_required=True,
            status="review_required",
        )

    reconciled_value = values[0]

    # LLM output alone is insufficient for automatic acceptance.
    if all(
        candidate.extraction_method == "llm"
        for candidate in usable
    ):
        return ReconciledKPIResult(
            metric=metric,
            value=reconciled_value,
            unit=resolved_unit,
            supporting_evidence=supporting_evidence,
            year=resolved_year,
            location=resolved_location,
            conflict_flag=False,
            review_required=True,
            status="review_required",
        )

    return ReconciledKPIResult(
        metric=metric,
        value=reconciled_value,
        unit=resolved_unit,
        supporting_evidence=supporting_evidence,
        year=resolved_year,
        location=resolved_location,
        conflict_flag=False,
        review_required=False,
        status="accepted",
    )

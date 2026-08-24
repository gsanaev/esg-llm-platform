from esg.core.types import EvidenceCandidate
from esg.pipeline.reconciliation import reconcile_metric_evidence


def _water_candidate(
    value,
    *,
    method="regex",
    year=None,
    location=None,
    unit="m3",
):
    return EvidenceCandidate(
        metric="water_withdrawal",
        value_raw=str(value) if value is not None else "unclear",
        value_normalized=value,
        unit_raw=unit,
        unit_normalized=unit,
        year=year,
        location=location,
        source_document="synthetic_report.pdf",
        extraction_method=method,
    )


def test_reconciliation_returns_not_reported_without_evidence():
    result = reconcile_metric_evidence(
        "water_withdrawal",
        [],
    )

    assert result.status == "not_reported"
    assert result.value is None
    assert result.conflict_flag is False
    assert result.review_required is False


def test_reconciliation_accepts_agreeing_deterministic_evidence():
    evidence = [
        _water_candidate(
            1_200_000.0,
            method="table_grid",
        ),
        _water_candidate(
            1_200_000.0,
            method="regex",
        ),
    ]

    result = reconcile_metric_evidence(
        "water_withdrawal",
        evidence,
    )

    assert result.status == "accepted"
    assert result.value == 1_200_000.0
    assert result.unit == "m3"
    assert result.conflict_flag is False
    assert result.review_required is False
    assert len(result.supporting_evidence) == 2


def test_reconciliation_flags_same_context_value_conflict():
    evidence = [
        _water_candidate(
            1_200_000.0,
            method="table_grid",
        ),
        _water_candidate(
            1_250_000.0,
            method="regex",
        ),
    ]

    result = reconcile_metric_evidence(
        "water_withdrawal",
        evidence,
    )

    assert result.status == "review_required"
    assert result.value is None
    assert result.conflict_flag is True
    assert result.review_required is True


def test_reconciliation_different_years_are_not_automatic_conflict():
    evidence = [
        _water_candidate(
            1_100_000.0,
            method="table_grid",
            year=2023,
        ),
        _water_candidate(
            1_200_000.0,
            method="table_grid",
            year=2024,
        ),
    ]

    result = reconcile_metric_evidence(
        "water_withdrawal",
        evidence,
    )

    assert result.status == "review_required"
    assert result.value is None
    assert result.conflict_flag is False
    assert result.review_required is True


def test_reconciliation_llm_only_requires_review():
    evidence = [
        _water_candidate(
            1_200_000.0,
            method="llm",
        )
    ]

    result = reconcile_metric_evidence(
        "water_withdrawal",
        evidence,
    )

    assert result.status == "review_required"
    assert result.value == 1_200_000.0
    assert result.conflict_flag is False
    assert result.review_required is True


def test_reconciliation_unparsed_evidence_requires_review():
    evidence = [
        _water_candidate(
            None,
            method="nlp",
        )
    ]

    result = reconcile_metric_evidence(
        "water_withdrawal",
        evidence,
    )

    assert result.status == "review_required"
    assert result.value is None
    assert result.conflict_flag is False
    assert result.review_required is True

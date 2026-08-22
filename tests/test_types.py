from esg.core.types import EvidenceCandidate


def test_evidence_candidate_preserves_quantitative_provenance():
    candidate = EvidenceCandidate(
        company_id="COMP_001",
        metric="water_withdrawal",
        value_raw="1.2 million",
        value_normalized=1_200_000.0,
        unit_raw="m3",
        unit_normalized="m3",
        year=2025,
        location="Frankfurt",
        source_document="synthetic_report.pdf",
        page=7,
        source_context="Water withdrawal was 1.2 million m3 in 2025.",
        extraction_method="regex",
        extraction_score=0.73,
    )

    assert candidate.metric == "water_withdrawal"
    assert candidate.value_raw == "1.2 million"
    assert candidate.value_normalized == 1_200_000.0
    assert candidate.unit_normalized == "m3"
    assert candidate.year == 2025
    assert candidate.page == 7
    assert candidate.extraction_method == "regex"


def test_evidence_candidate_supports_qualitative_values():
    candidate = EvidenceCandidate(
        company_id="COMP_001",
        metric="water_dependency",
        value_raw="high dependency on local groundwater",
        value_normalized="high dependency",
        source_document="synthetic_report.pdf",
        page=4,
        source_context="Operations have a high dependency on local groundwater.",
        extraction_method="nlp",
        extraction_score=0.60,
    )

    assert candidate.value_normalized == "high dependency"
    assert candidate.unit_normalized is None
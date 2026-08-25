from esg.normalization.regex_normalizer import normalize_regex_result
from esg.pipeline.evidence import (
    normalized_results_to_evidence,
    raw_candidate_results_to_evidence,
)
from esg.normalization.table_plain_normalizer import (
    normalize_table_plain_result,
)


def test_normalized_result_becomes_evidence_candidate():
    normalized = {
        "water_withdrawal": {
            "raw_value": "1.2 million",
            "raw_unit": "m³",
            "value": 1_200_000.0,
            "unit": "m3",
            "_score": {"score": 0.72},
            "company_id": "synthetic_alpha",
            "year": 2024,
            "location": "Frankfurt facility",
            "page": 7,
            "source_context": "Water Withdrawal | m³ | 1.2 million",
        }
    }

    evidence = normalized_results_to_evidence(
        normalized,
        source_document="synthetic_report.pdf",
        extraction_method="regex",
    )

    assert len(evidence) == 1

    candidate = evidence[0]

    assert candidate.metric == "water_withdrawal"
    assert candidate.value_raw == "1.2 million"
    assert candidate.value_normalized == 1_200_000.0
    assert candidate.unit_raw == "m³"
    assert candidate.unit_normalized == "m3"
    assert candidate.source_document == "synthetic_report.pdf"
    assert candidate.extraction_method == "regex"
    assert candidate.extraction_score == 0.72
    assert candidate.company_id == "synthetic_alpha"
    assert candidate.year == 2024
    assert candidate.location == "Frankfurt facility"

    assert candidate.page == 7
    assert candidate.source_context == "Water Withdrawal | m³ | 1.2 million"


def test_unparsed_observation_is_still_preserved_as_evidence():
    normalized = {
        "energy_consumption": {
            "raw_value": "unclear",
            "raw_unit": "MWh",
            "value": None,
            "unit": "MWh",
            "_score": {"score": 0.0},
        }
    }

    evidence = normalized_results_to_evidence(
        normalized,
        source_document="synthetic_report.pdf",
        extraction_method="nlp",
    )

    assert len(evidence) == 1
    assert evidence[0].value_raw == "unclear"
    assert evidence[0].value_normalized is None


def test_plural_raw_candidates_become_separate_evidence_candidates():
    raw_candidates = {
        "water_withdrawal": [
            {
                "raw_value": "1,200,000",
                "raw_unit": "m3",
                "confidence": 0.6,
            },
            {
                "raw_value": "1,250,000",
                "raw_unit": "m3",
                "confidence": 0.6,
            },
        ]
    }

    kpi_schema = {
        "water_withdrawal": {
            "canonical_unit": "m3",
            "accepted_units": ["m3"],
        }
    }

    evidence = raw_candidate_results_to_evidence(
        raw_candidates,
        kpi_schema=kpi_schema,
        normalizer=normalize_regex_result,
        source_document="synthetic_report.pdf",
        extraction_method="regex",
    )

    assert len(evidence) == 2

    assert [candidate.value_raw for candidate in evidence] == [
        "1,200,000",
        "1,250,000",
    ]

    assert [candidate.value_normalized for candidate in evidence] == [
        1_200_000.0,
        1_250_000.0,
    ]

    assert all(
        candidate.unit_normalized == "m3"
        for candidate in evidence
    )
    assert all(
        candidate.extraction_method == "regex"
        for candidate in evidence
    )


def test_plural_adapter_preserves_raw_location_context():
    raw_candidates = {
        "water_withdrawal": [
            {
                "raw_value": "350,000",
                "raw_unit": "m3",
                "confidence": 0.85,
                "company_id": "synthetic_alpha",
                "year": 2024,
                "location": "Frankfurt facility",
                "page": 3,
                "source_context": (
                    "Frankfurt facility | "
                    "Total water withdrawal | m3 | 350,000"
                ),
            }
        ]
    }

    kpi_schema = {
        "water_withdrawal": {
            "canonical_unit": "m3",
            "accepted_units": ["m3"],
        }
    }

    evidence = raw_candidate_results_to_evidence(
        raw_candidates,
        kpi_schema=kpi_schema,
        normalizer=normalize_table_plain_result,
        source_document="synthetic_report.pdf",
        extraction_method="table_plain",
    )

    assert len(evidence) == 1

    candidate = evidence[0]

    assert candidate.value_normalized == 350_000.0
    assert candidate.unit_normalized == "m3"
    assert candidate.company_id == "synthetic_alpha"
    assert candidate.year == 2024
    assert candidate.location == "Frankfurt facility"
    assert candidate.page == 3
    assert candidate.source_context == (
        "Frankfurt facility | "
        "Total water withdrawal | m3 | 350,000"
    )

from esg.pipeline.evidence import normalized_results_to_evidence


def test_normalized_result_becomes_evidence_candidate():
    normalized = {
        "water_withdrawal": {
            "raw_value": "1.2 million",
            "raw_unit": "m³",
            "value": 1_200_000.0,
            "unit": "m3",
            "_score": {"score": 0.72},
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

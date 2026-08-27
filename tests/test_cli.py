from __future__ import annotations

import json
import sys

from esg.cli import run
from esg.core.types import EvidenceCandidate, ReconciledKPIResult


def test_cli_writes_reconciled_results(monkeypatch, tmp_path):
    evidence = EvidenceCandidate(
        metric="water_withdrawal",
        source_document="report.pdf",
        extraction_method="regex",
        value_raw="1,200,000",
        value_normalized=1_200_000.0,
        unit_raw="m3",
        unit_normalized="m3",
        year=2024,
        location="Frankfurt facility",
        extraction_score=0.9,
    )

    reconciled = ReconciledKPIResult(
        metric="water_withdrawal",
        value=1_200_000.0,
        unit="m3",
        supporting_evidence=(evidence,),
        year=2024,
        location="Frankfurt facility",
        conflict_flag=False,
        review_required=False,
        status="accepted",
    )

    monkeypatch.setattr(
        run.ESGPipeline,
        "run_on_pdf_reconciled",
        lambda self, pdf_path: [reconciled],
    )

    output_path = tmp_path / "result.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "esg-extract",
            "report.pdf",
            "--output",
            str(output_path),
        ],
    )

    run.main()

    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["pdf_path"] == "report.pdf"

    assert data["results"] == [
        {
            "metric": "water_withdrawal",
            "value": 1_200_000.0,
            "unit": "m3",
            "year": 2024,
            "location": "Frankfurt facility",
            "conflict_flag": False,
            "review_required": False,
            "status": "accepted",
            "supporting_evidence": [
                {
                    "metric": "water_withdrawal",
                    "source_document": "report.pdf",
                    "extraction_method": "regex",
                    "company_id": None,
                    "value_raw": "1,200,000",
                    "value_normalized": 1_200_000.0,
                    "unit_raw": "m3",
                    "unit_normalized": "m3",
                    "year": 2024,
                    "location": "Frankfurt facility",
                    "page": None,
                    "source_context": None,
                    "extraction_score": 0.9,
                }
            ],
        }
    ]

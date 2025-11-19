import csv
from pathlib import Path
from typing import List
from esg.core.types import KPIResult


def save_results_to_csv(results: List[KPIResult], out_path: str) -> None:
    """
    Save pipeline results to a CSV file with a stable, flat schema.
    """
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["code", "value", "unit", "confidence", "source"])

        for r in results:
            writer.writerow([
                r.code,
                r.value,
                r.unit,
                r.confidence,
                ",".join(r.source),
            ])

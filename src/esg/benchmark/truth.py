from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_benchmark_truth(path: str | Path) -> dict[str, Any]:
    """
    Load benchmark-only hidden ground truth.

    Ground truth is used for synthetic benchmark generation and later
    evaluation. It must not be passed to the extraction pipeline.
    """
    truth_path = Path(path)

    with truth_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Benchmark truth must be a mapping.")

    if not isinstance(data.get("companies"), list):
        raise ValueError("Benchmark truth must contain a companies list.")

    return data

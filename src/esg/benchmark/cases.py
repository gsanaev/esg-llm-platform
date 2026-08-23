from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_benchmark_cases(path: str | Path) -> list[dict[str, Any]]:
    """
    Load controlled synthetic benchmark case definitions.

    Case definitions describe how hidden company truth is disclosed.
    They must not duplicate or replace the benchmark ground truth.
    """
    cases_path = Path(path)

    with cases_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Benchmark cases must be a mapping.")

    cases = data.get("benchmark_cases")

    if not isinstance(cases, list):
        raise ValueError(
            "Benchmark cases must contain a benchmark_cases list."
        )

    return cases

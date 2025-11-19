# src/esg/config.py
from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import json
import yaml
import logging
import os

# Load .env as early as possible
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = BASE_DIR / "schemas"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class ESGConfig:
    def __init__(self):
        # Only universal_kpis.json exists in esg/schemas
        self.universal_kpis = load_json(SCHEMA_DIR / "universal_kpis.json")


def load_config():
    return ESGConfig()


def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger. Safe to call multiple times.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


# Run once automatically
setup_logging()

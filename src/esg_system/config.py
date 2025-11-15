import json
import yaml
from pathlib import Path
import logging

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
        self.universal_kpis = load_json(SCHEMA_DIR / "universal_kpis.json")
        self.gri_kpis = load_json(SCHEMA_DIR / "gri_kpis.json")
        self.sasb_kpis = load_json(SCHEMA_DIR / "sasb_kpis.json")
        self.mapping_rules = load_yaml(SCHEMA_DIR / "mapping_rules.yaml")


def load_config():
    return ESGConfig()

def setup_logging(level: str = "INFO") -> None:
    """
    Configure root logger for the entire ESG-LM platform.
    Safe to call multiple times.
    """

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

# Run once when importing config
setup_logging()
import json
import yaml
from pathlib import Path

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

from pathlib import Path

def ensure_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def read_text_file(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_text_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

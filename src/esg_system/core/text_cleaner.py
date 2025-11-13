import re

def clean_text(text: str) -> str:
    """Basic text normalization for cleaner extraction."""
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"-\s+", "", text)  # fix broken hyphenation
    return text.strip()

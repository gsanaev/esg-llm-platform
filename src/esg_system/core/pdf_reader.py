import pdfplumber

def extract_text(pdf_path: str) -> str:
    """Extract plain text from a PDF file using pdfplumber."""
    full_text = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text.append(text)

    return "\n".join(full_text)

import pdfplumber

def extract_tables(pdf_path: str):
    """Extract tables from a PDF as lists of lists."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables
